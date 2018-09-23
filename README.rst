========
Overview
========

CLI tool to deploy Scrapy projects to SpiderKeeper

Installation
============

PyPi

::

    pip install spiderkeeper-deploy


Usage
=====

Config values can be supplied at runtime as arguments. If arguments are not supplied
spiderkeeper-deploy will try to find scrapy.cfg in the current project. Config values
in scrapy.cfg will be loaded from [skdeploy] section. Any value not supplied as argument
or in scrapy.cfg can be entered in the interactive prompt.

The one caveat to using scrapy.cfg is that passwords will not be read. They must be supplied
at run time or set in SK_PASSWORD environment variable. Don't save passwords in config files!

::

    spiderkeeper-deploy --help

    Usage: spiderkeeper-deploy [OPTIONS]

        Deploy Scrapy projects to SpiderKeeper.

        Hint: you can define CLI args in scrapy.cfg file in your project.

        CLI args override scrapy.cfg

    Options:
        -u, --url       Server name or ip. Default: http://localhost:8080
        -p, --project   Project name.
        -j, --jobs      Jobs in json format
        --user          Default: admin
        --password      Will use ENV SK_PASSWORD if present. Default: admin
        --help          Show this message and exit.

Example scrapy.cfg
------------------

Note: jobs format is exactly the same as the api provided by SpiderKeeper to add and update jobs.
This array must be indented at least 1 level. Proper JSON formatting is required so double quotes
and no trailing comma.

::

    [settings]
    default = project.settings

    [deploy]
    url = http://localhost:6800/
    project = project

    [skdeploy]
    url = http://localhost:5000/
    project = project
    user = me
    jobs = [
            {
                "spider_name": "spider_name",
                "spider_arguments": "arg1,arg2",
                "run_type": "periodic",
                "desc": "description",
                "tags": "tag1,tag2",
                "priority": 1,
                "cron_minutes": "0",
                "cron_hour": "*",
                "cron_day_of_month": "*",
                "cron_day_of_week": "*",
                "cron_month": "*"
            }
        ]

Deploying
=========

- If the project does not already exist it will be created
- Any jobs not yet in SpiderKeeper will be added
- Jobs already in SpiderKeeper will be updated (i.e. tags, desc can be updated)
- **Jobs not in config will be deleted**

A job is defined as already existing in SpiderKeeper if spider_name,
spider_arguments, cron_minutes, cron_hour, cron_day_of_month, cron_day_of_week,
and cron_month all match what is in config.

Note: spider_name is always required. spider_arguments can be omitted and will
default to None. cron settings can be omitted and will default to "*"

SpiderKeeper uses numbers to identify projects. This means it is possible to
have two projects with the same name. spiderkeeper-deploy will use the first
project who's name matches the project config value. If you have an existing
deployment with duplicates you should keep this in mind. If not you should
never get duplicates as long as you only use spiderkeeper-deploy. It is still
possible to get duplicates with a manual deployment.
