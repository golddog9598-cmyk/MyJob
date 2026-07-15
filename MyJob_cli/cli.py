"""MyJob maintenance CLI.

Recruitment-platform commands live exclusively in the Vue workspace and the
browser extension, not in this server-side CLI.
"""

import json
import webbrowser
from pathlib import Path

import click

from . import client, output


@click.group()
def main():
    """Manage the MyJob service and user resume files."""


@main.command("status")
def status_command():
    """Check the MyJob account/resume backend."""
    output.emit(output.ok_or_fail(client.health(), "status"))


@main.command("open")
def open_command():
    """Open the authenticated Vue workspace."""
    webbrowser.open(f"{client.BASE_URL}/app")
    output.emit(output.ok("open", {"url": f"{client.BASE_URL}/app"}))


@main.group("resume")
def resume_group():
    """Inspect and export the current user's main resume."""


@resume_group.command("show")
def resume_show():
    output.emit(output.ok_or_fail(client.get_master_resume(), "resume-show"))


@resume_group.command("templates")
def resume_templates():
    output.emit(output.ok_or_fail(client.get_resume_templates(), "resume-templates"))


@resume_group.command("upload")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--template", "template_id", default="ats_classic", show_default=True)
def resume_upload(file_path, template_id):
    output.emit(output.ok_or_fail(client.upload_master_resume(file_path, template_id), "resume-upload"))


@resume_group.command("template")
@click.argument("template_id")
def resume_template(template_id):
    output.emit(output.ok_or_fail(client.set_master_resume_template(template_id), "resume-template"))


@resume_group.command("export")
@click.option("--format", "output_format", type=click.Choice(["docx", "pdf"]), default="docx")
@click.option("--template", "template_id", default="")
@click.option("--output", "output_path", type=click.Path(dir_okay=False), required=True)
def resume_export(output_format, template_id, output_path):
    response = client.export_master_resume(output_format, template_id)
    if response.is_error:
        output.emit(output.fail("resume-export", f"HTTP {response.status_code}: {response.text[:200]}"))
        return
    target = Path(output_path)
    target.write_bytes(response.content)
    output.emit(output.ok("resume-export", {"path": str(target.resolve()), "format": output_format}))


@main.command("architecture")
def architecture_command():
    """Print the enforced data boundary."""
    output.emit(output.ok("architecture", {
        "backend": ["MyJob account", "administrator analytics", "main resume", "static Vue files"],
        "client": ["platform login", "job search", "applications", "conversations", "campaigns", "platform statistics"],
        "client_storage": "IndexedDB",
    }))


if __name__ == "__main__":
    main()
