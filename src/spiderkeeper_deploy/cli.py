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
