"""lakejob CLI — BOSS直聘自动化命令行工具."""

import sys
import click


@click.group()
def main():
    """lakejob — BOSS直聘岗位雷达 CLI"""


@main.command("version")
def version():
    """Print version."""
    click.echo("lakejobai-job-radar v0.1.0")


if __name__ == "__main__":
    main()
