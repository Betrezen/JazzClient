"""
author: krozin@gmail.com. 2017.
"""

import json
import os
import sys
import yaml

import click
from pyclient import rtc_web_client

from rtc2xlsx import bugs2excel

READABLE_FILE = click.Path(
    dir_okay=False, readable=True, exists=True, resolve_path=True)
WRITABLE_FILE = click.Path(
    dir_okay=False, writable=True, resolve_path=True)

CUSTOMER = 'ibm'
RTC_URI = "https://ccm1.cloud.{}.com/jazz".format(CUSTOMER)
RTC_QUERRY_ID = "_zJceECs7Eee2JMMBDF4566"
RTC_PROJECT_ID = '_9qwq0PATEeOOedCg5mWE15'


@click.command()
@click.option('--rtc-uri', default=RTC_URI, help='RTC URI.')
@click.option('--user', prompt='RTC username', help='RTC login user.')
@click.option('--password', prompt='RTC password', help='RTC password.',
              hide_input=True)
@click.option('--rtc-querry-id', default=RTC_QUERRY_ID, help='RTC querry ID.')
@click.option('--rtc-project-id', default=RTC_PROJECT_ID,
              help='RTC project ID.')
@click.option('--teams', type=READABLE_FILE,
              help='JSON/YAML File with team lists')
@click.option('--use-cache', is_flag=True,
              help='Use woritems from cache file if it is present.')
@click.argument('output', type=WRITABLE_FILE)
def main(rtc_uri, user, password, rtc_querry_id, rtc_project_id,
         use_cache, teams, output):
    """Dump RTC workitems to xlsx file."""
    cache_file = 'cache_{}_{}.json'.format(rtc_project_id, rtc_querry_id)

    if use_cache and os.path.exists(cache_file):
        with open(cache_file) as f:
            workitems = json.load(f)
        click.echo("Loaded %s" % cache_file)

    else:
        client = rtc_web_client.RTCWebClient(
            url=rtc_uri,
            user=user,
            password=password,
            querryid=rtc_querry_id,
            projectid=rtc_project_id)
        workitems = client.get_workitems()

        with open(cache_file, 'w') as f:
            json.dump(workitems, f, indent=4)
            click.echo("Saved %s" % cache_file)

    if not workitems:
        click.echo("Failed to load workitems")
        sys.exit(1)

    click.echo("Found %s workitems" % len(workitems))

    teams_dict = {}
    if teams:
        with open(teams) as f:
            teams_dict = yaml.load(f)
        click.echo("Loaded %s teams" % len(teams_dict))

    bug_dumper = bugs2excel.Bugs2Excel(workitems, teams=teams_dict)
    bug_dumper.save_bugs_to_file(output)

    click.echo("Saved %s" % output)
