import os
import sys
import glob
import json
import click
import shutil
import tempfile
import configparser
import requests as req
from typing import List, Tuple, Dict
from subprocess import check_call
from scrapyd_client import deploy
from requests.auth import HTTPBasicAuth
from scrapy.utils.python import retry_on_eintr
from scrapy.utils.conf import get_config, closest_scrapy_cfg

PROJECTS_PATH = '/api/projects'
UPLOAD_PATH = '/project/{}/spider/upload'
JOBS_PATH = '/api/projects/{}/jobs'
UPDATE_JOB_PATH = '/api/projects/{}/jobs/{}'
DEL_JOB_PATH = '/project/{}/job/{}/remove'


@click.command()
def main():
    '''spiderkeeper-deploy cli method'''
    url = get_option('skdeploy', 'url').rstrip('/')
    project = get_option('skdeploy', 'project')
    jobs = json.loads(get_option("skdeploy", "jobs"))

    auth = ('admin', 'admin')

    project_id = get_project_id(url, project, auth)

    if project_id == None:
         project_id = create_project(url, project, auth)

    filename = build_egg(project)
    upload_file(url, project_id, filename, auth)

    update_jobs(url, project_id, jobs, auth)


def get_project_id(url: str, project: str, auth: Tuple[str, str]):
    '''Gets project id if it exists else returns None'''
    resp = req.get(url + PROJECTS_PATH, auth=auth)

    if resp.status_code != 200:
        click.echo('Unable to get projects list')
        click.echo(f'SpiderKeeper returned {resp.status_code}')
        exit(1)

    projects_json= resp.json()

    for p in projects_json:
        if p['project_name'] == project:
            return p['project_id']

    return None


def create_project(url: str, project: str, auth: Tuple[str, str]):
    '''Creates project in SpiderKeeper and returns id'''
    params = {'project_name': project}
    resp = req.post(url + PROJECTS_PATH, data=params, auth=auth)

    if resp.status_code != 200:
        click.echo('Unable to create project')
        click.echo(f'SpiderKeeper returned {resp.status_code}')
        exit(1)

    project_json = resp.json()
    return project_json['project_id']


def upload_file(url: str, project_id: int, filename: str, auth: Tuple[str, str]):
    '''Uploads egg to SpiderKeeper'''
    upload_url = url + UPLOAD_PATH.format(project_id)

    with open(filename, 'rb') as f:
        files = { 'file': f }
        referer = url
        headers = { 'Referer': referer }
        resp = req.post(upload_url, files=files, auth=auth, headers=headers)

        if resp.status_code != 200:
            click.echo('Unable to create project')
            click.echo(f'SpiderKeeper returned {resp.status_code}')
            exit(1)


def update_jobs(url: str, project_id: int, jobs: dict, auth: Tuple[str, str]):
    '''Deleted all jobs and readd.

    Jobs in scrapy.cfg should be in the following format.
    Note: all newlines must be indented at least 1 level.

    jobs = [
            {
                "spider_name": "spider1",
                "spider_arguments": "arg1,arg2",
                "desc": "description",
                "run_type": "periodic",
                "priority": "0",
                "cron_minutes": "5",
                "cron_hour": "*",
                "cron_day_of_month": "*",
                "cron_day_of_week": "*",
                "cron_month": "*"
            }
        ]

    run_type can be "onetime" or "periodic"

    priority can be -1, 0, 1, or 2. -1 = Low, 0 = Normal, 1 = High, 2 = Highest
    '''
    resp = req.get(url + JOBS_PATH.format(project_id), auth=auth)

    if resp.status_code != 200:
        click.echo('Unable to create jobs')
        click.echo(f'SpiderKeeper returned {resp.status_code}')
        exit(1)

    old_jobs = resp.json()

    (add, merge, delete) = get_job_list_matches(jobs, old_jobs)

    add_jobs(url, project_id, add, auth)
    merge_jobs(url, project_id, merge, auth)
    del_jobs(url, project_id, delete, auth)


def add_jobs(url: str, project_id: int, jobs: List[Dict[str, str]], auth: Tuple[str, str]):
    '''Adds jobs to SpiderKeeper'''

    for job in jobs:
        resp = req.post(url + JOBS_PATH.format(project_id), data=job, auth=auth)

        if resp.status_code != 200:
            click.echo('Error while deleting old jobs. Jobs are in an inconsistant state.')
            click.echo('Sorry about that :(')
            click.echo(f'SpiderKeeper returned {resp.status_code}')
            exit(1)


def merge_jobs(url: str, project_id: int, jobs: List[Dict[str, str]], auth: Tuple[str, str]):
    '''Updates jobs in SpiderKeeper'''

    for job in jobs:
        job_id = job.pop('job_instance_id')
        resp = req.put(url + UPDATE_JOB_PATH.format(project_id, job_id), data=job, auth=auth)

        if resp.status_code != 200:
            click.echo('Error while deleting old jobs. Jobs are in an inconsistant state.')
            click.echo('Sorry about that :(')
            click.echo(f'SpiderKeeper returned {resp.status_code}')
            exit(1)


def del_jobs(url: str, project_id: int, jobs: List[Dict[str, str]], auth: Tuple[str, str]):
    '''Deletes jobs from SpiderKeeper'''
    referer = url
    headers = { 'Referer': referer }

    for job in jobs:
        job_id = job['job_instance_id']
        resp = req.get(url + DEL_JOB_PATH.format(project_id, job_id), headers=headers, auth=auth)

        if resp.status_code != 200:
            click.echo('Error while deleting old jobs. Jobs are in an inconsistant state.')
            click.echo('Sorry about that :(')
            click.echo(f'SpiderKeeper returned {resp.status_code}')
            exit(1)


def get_job_list_matches(jobs: List[Dict[str, str]], old_jobs: List[Dict[str, str]]):
    '''
    Takes jobs from scrapy.cfg and compares them to jobs already in SpiderKeeper.
    A job matches if it has the same cron settings. Returns tuple (add, merge, delete)

    add: Jobs in scrapy.cfg and not yet in SpiderKeeper

    merge: Jobs in both scrapy.cfg and SpiderKeeper

    delete: Jobs not in scrapy.cfg but is in SpiderKeeper
    '''
    merge = []
    delete = []

    for old_job in old_jobs:
        old_job_cron_info = {k: old_job[k] for k in old_job if k.startswith('cron_')}

        for job in jobs:
            job_cron_info = {k: job[k] for k in job if k.startswith('cron_')}

            # job exists in both new and old
            if job_cron_info == old_job_cron_info:
                job['job_instance_id'] = old_job['job_instance_id']
                merge.append(job)
                break
        else:
            # old_job does not exists in new jobs list
            delete.append(old_job)

    # anything left must be added
    add = [job for job in jobs if 'job_instance_id' not in job]

    return (add, merge, delete)

def get_option(section: str, option: str, default: str = None):
    '''Gets option from scrapy.cfg in project root'''
    cfg = get_config()
    return cfg.get(section, option) if cfg.has_option(section, option) else default


def build_egg(project: str):
    '''Build egg in project root'''
    closest = closest_scrapy_cfg()

    if closest == '':
        click.echo('No setup.py found')
        exit(1)

    directory = os.path.dirname(closest)
    os.chdir(directory)

    if not os.path.exists('setup.py'):
        click.echo('No setup.py in project')
        exit(1)

    d = tempfile.mkdtemp(prefix="scrapydeploy-")

    with open(os.path.join(d, "stdout"), "wb") as o, open(os.path.join(d, "stderr"), "wb") as e:
        p = [sys.executable, 'setup.py', 'clean', '-a', 'bdist_egg', '-d', d]
        retry_on_eintr(check_call, p, stdout=o, stderr=e)

    egg = glob.glob(os.path.join(d, '*.egg'))[0]
    filename = f'{project}.egg'
    shutil.copyfile(egg, filename)
    return f'{directory}/{filename}'


if __name__ == '__main__':
    main()
