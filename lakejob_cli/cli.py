"""MyJob CLI - 求职自动化命令行工具."""

import json
import os
import sys
import click
from pathlib import Path

from . import client, output


@click.group()
def main():
    """MyJob - 求职自动化平台 V0.0.3

    命令返回结构化 JSON 到 stdout，Agent 友好。
    """


# ── 版本 ──
@main.command("version")
def version_cmd():
    output.emit(output.ok("version", data={"name": "MyJob", "version": "V0.0.3"}))


# ── Schema：AI Agent 工具描述 ──
@main.command("schema")
def schema_cmd():
    path = __file__.replace("cli.py", "schema.json")
    with open(path, encoding="utf-8") as f:
        schema = json.load(f)
    output.emit(output.ok("schema", data=schema))


# ── 搜索 ──
@main.command("search")
@click.argument("keyword")
@click.option("--city", default="", help="城市名（空则使用设置中的默认城市）")
@click.option("--welfare", default=None, help="福利筛选 如 双休,五险一金")
@click.option("--count", type=int, default=60, help="返回条数上限")
def search_cmd(keyword, city, welfare, count):
    """搜索BOSS直聘岗位。"""
    payload = {"keyword": keyword, "city": city or "", "limit": count}
    if welfare:
        payload["welfare"] = welfare
    resp = client.search(keyword, city, count)
    result = output.ok_or_fail(resp, "search")
    output.emit(result)


# ── 状态 ──
@main.command("status")
def status_cmd():
    resp = client.status()
    result = output.ok_or_fail(resp, "status")
    output.emit(result)


# ── 投递漏斗 ──
@main.command("stats")
def stats_cmd():
    resp = client.stats()
    result = output.ok_or_fail(resp, "stats")
    output.emit(result)


# ── 岗位列表 ──
@main.command("jobs")
@click.option("--status", "filter_status", default=None, help="pending / applied / replied")
@click.option("--limit", type=int, default=50)
def jobs_cmd(filter_status, limit):
    resp = client.jobs(filter_status, limit)
    result = output.ok_or_fail(resp, "jobs")
    output.emit(result)


# ── 投递单个 ──
@main.command("apply")
@click.argument("job_url")
def apply_cmd(job_url):
    resp = client.apply_one(job_url)
    result = output.ok_or_fail(resp, "apply")
    output.emit(result)


# ── 批量投递 ──
@main.command("apply-batch")
@click.option("--status", "filter_status", default="pending", help="pending 等状态")
def apply_batch_cmd(filter_status):
    r = client.jobs(filter_status, limit=200)
    if r.is_error:
        output.emit(output.fail("apply-batch", f"fetch jobs failed: {r.status_code}"))
        return
    jobs_list = r.json().get("jobs", [])
    urls = [j["job_url"] for j in jobs_list if j.get("job_url")]
    if not urls:
        output.emit(output.fail("apply-batch", "no job_urls found"))
        return
    resp = client.apply_batch(urls)
    result = output.ok_or_fail(resp, "apply-batch")
    output.emit(result)


# ── 扫描当前页面 ──
@main.command("scan")
def scan_cmd():
    """扫描当前BOSS搜索结果页，提取所有可见岗位。"""
    resp = client.scan()
    result = output.ok_or_fail(resp, "scan")
    output.emit(result)


# ── 扫描并一键投递 ──
@main.command("scan-apply")
def scan_apply_cmd():
    """扫描当前页面全部岗位并一键批量投递。"""
    resp = client.scan_and_apply()
    result = output.ok_or_fail(resp, "scan-apply")
    output.emit(result)


# ── 会话列表 ──
@main.command("conversations")
def conversations_cmd():
    resp = client.conversations()
    result = output.ok_or_fail(resp, "conversations")
    output.emit(result)


# ── 聊天记录 ──
@main.command("chat")
@click.argument("conv_id", type=int)
def chat_cmd(conv_id):
    resp = client.chat_messages(conv_id)
    result = output.ok_or_fail(resp, "chat")
    output.emit(result)


# ── 手动发消息 ──
@main.command("send")
@click.argument("conv_id", type=int)
@click.option("--msg", required=True, help="消息内容")
def send_cmd(conv_id, msg):
    resp = client.send_message(conv_id, msg)
    result = output.ok_or_fail(resp, "send")
    output.emit(result)


# ── 诊断 ──
@main.command("doctor")
def doctor_cmd():
    resp = client.doctor()
    result = output.ok_or_fail(resp, "doctor")
    output.emit(result)


# ── 扫码登录 ──
@main.command("login")
def login_cmd():
    resp = client.relogin()
    result = output.ok_or_fail(resp, "login")
    output.emit(result)


# ── AI JD分析 ──
@main.command("analyze")
@click.argument("job_url")
@click.option("--title", default="", help="岗位名称")
@click.option("--company", default="", help="公司名")
@click.option("--desc", default="", help="JD描述")
def analyze_cmd(job_url, title, company, desc):
    resp = client.analyze(job_url, title, company, desc)
    output.emit(output.ok_or_fail(resp, "analyze"))


# ── 主简历 / JD 定制简历 ──
@main.group("resume")
def resume_group():
    """管理主简历和按 JD 生成的定制简历。"""


@resume_group.command("show")
def resume_show_cmd():
    output.emit(output.ok_or_fail(client.get_master_resume(), "resume-show"))


@resume_group.command("templates")
def resume_templates_cmd():
    """列出内置简历模板库。"""
    output.emit(output.ok_or_fail(client.get_resume_templates(), "resume-templates"))


@resume_group.command("set")
@click.option("--file", "file_path", required=True, type=click.Path(exists=True, dir_okay=False), help="UTF-8 简历文件")
@click.option("--name", default="主简历", help="简历名称")
def resume_set_cmd(file_path, name):
    content = Path(file_path).read_text(encoding="utf-8")
    suffix = Path(file_path).suffix.lower().lstrip(".") or "markdown"
    output.emit(output.ok_or_fail(client.save_master_resume(content, name, suffix), "resume-set"))


@resume_group.command("upload")
@click.option("--file", "file_path", required=True, type=click.Path(exists=True, dir_okay=False), help="DOCX/PDF/TXT/MD/HTML/RTF/JSON/ODT")
@click.option("--template", "template_id", default="ats_classic", help="模板 ID")
def resume_upload_cmd(file_path, template_id):
    """上传并解析多格式简历，套用所选模板。"""
    output.emit(output.ok_or_fail(client.upload_master_resume(file_path, template_id), "resume-upload"))


@resume_group.command("template")
@click.argument("template_id")
def resume_template_cmd(template_id):
    """设置主简历和后续 JD 定制稿使用的模板。"""
    output.emit(output.ok_or_fail(client.set_master_resume_template(template_id), "resume-template"))


@resume_group.command("export")
@click.option("--format", "output_format", type=click.Choice(["docx", "pdf", "html", "md", "txt"]), default="docx")
@click.option("--template", "template_id", default="", help="临时指定模板 ID")
@click.option("--output", "output_path", required=True, type=click.Path(dir_okay=False))
def resume_export_cmd(output_format, template_id, output_path):
    """导出主简历为 DOCX/PDF/HTML/Markdown。"""
    resp = client.export_master_resume(output_format, template_id)
    if resp.is_error:
        output.emit(output.fail("resume-export", f"HTTP {resp.status_code}: {resp.text[:200]}"))
        return
    Path(output_path).write_bytes(resp.content)
    output.emit(output.ok("resume-export", data={"saved_to": str(Path(output_path).resolve()), "format": output_format}))


@resume_group.command("tailor")
@click.option("--job-url", required=True, help="岗位 URL")
@click.option("--title", default="", help="岗位名称（数据库已有时可省略）")
@click.option("--company", default="", help="公司名称")
@click.option("--city", default="", help="城市")
@click.option("--desc", default="", help="JD 文本（数据库已有时可省略）")
@click.option("--output", "output_path", type=click.Path(dir_okay=False), help="把 Markdown 定制稿写入文件")
def resume_tailor_cmd(job_url, title, company, city, desc, output_path):
    resp = client.tailor_resume(job_url, title, company, city, desc)
    result = output.ok_or_fail(resp, "resume-tailor")
    if not resp.is_error and output_path:
        data = resp.json().get("tailored_resume") or {}
        Path(output_path).write_text(data.get("content") or "", encoding="utf-8")
        result.setdefault("hints", {})["saved_to"] = str(Path(output_path).resolve())
    output.emit(result)


@resume_group.command("list")
@click.option("--job-url", default="", help="只看某岗位的定制版本")
def resume_list_cmd(job_url):
    output.emit(output.ok_or_fail(client.get_tailored_resumes(job_url), "resume-list"))


@resume_group.command("approve")
@click.argument("resume_id", type=int)
def resume_approve_cmd(resume_id):
    output.emit(output.ok_or_fail(client.set_tailored_resume_status(resume_id, "approved"), "resume-approve"))


# ── 求职计划 ──
@main.group("campaign")
def campaign_group():
    """按岗位和城市持续搜索、筛选、定制简历并跟踪面试。"""


@campaign_group.command("create")
@click.option("--name", default="求职计划")
@click.option("--keyword", "keywords", multiple=True, required=True, help="目标岗位，可重复传入")
@click.option("--city", "cities", multiple=True, required=True, help="目标城市，可重复传入")
@click.option("--min-score", default=60, type=click.IntRange(0, 100), help="最低匹配分")
@click.option("--max-jobs", default=10, type=click.IntRange(1, 50), help="每轮最多处理岗位数")
@click.option("--interval-hours", default=24, type=click.IntRange(1, 168), help="自动运行间隔")
@click.option("--no-tailor", is_flag=True, help="不自动生成 JD 定制简历")
@click.option("--auto-apply", is_flag=True, help="匹配后自动投递；仍受每日上限和风控约束")
@click.option("--confirm-auto-apply", is_flag=True, help="确认允许计划自动投递")
@click.option("--start", is_flag=True, help="创建后立即启用定时运行")
def campaign_create_cmd(name, keywords, cities, min_score, max_jobs, interval_hours, no_tailor, auto_apply, confirm_auto_apply, start):
    if auto_apply and not confirm_auto_apply:
        output.emit(output.fail("campaign-create", "自动投递需要同时传 --confirm-auto-apply"))
        return
    payload = {
        "name": name,
        "keywords": list(keywords),
        "cities": list(cities),
        "min_match_score": min_score,
        "max_jobs_per_run": max_jobs,
        "auto_tailor": not no_tailor,
        "apply_mode": "automatic" if auto_apply else "review",
        "auto_apply_confirmed": bool(auto_apply and confirm_auto_apply),
        "interval_hours": interval_hours,
        "status": "active" if start else "paused",
    }
    output.emit(output.ok_or_fail(client.create_campaign(payload), "campaign-create"))


@campaign_group.command("list")
def campaign_list_cmd():
    output.emit(output.ok_or_fail(client.get_campaigns(), "campaign-list"))


@campaign_group.command("show")
@click.argument("campaign_id", type=int)
def campaign_show_cmd(campaign_id):
    output.emit(output.ok_or_fail(client.get_campaign(campaign_id), "campaign-show"))


@campaign_group.command("run")
@click.argument("campaign_id", type=int)
def campaign_run_cmd(campaign_id):
    output.emit(output.ok_or_fail(client.run_campaign(campaign_id), "campaign-run"))


@campaign_group.command("resume")
@click.argument("campaign_id", type=int)
def campaign_resume_cmd(campaign_id):
    output.emit(output.ok_or_fail(client.set_campaign_status(campaign_id, "active"), "campaign-resume"))


@campaign_group.command("pause")
@click.argument("campaign_id", type=int)
def campaign_pause_cmd(campaign_id):
    output.emit(output.ok_or_fail(client.set_campaign_status(campaign_id, "paused"), "campaign-pause"))


# ── 候选池 ──
@main.command("shortlist")
@click.argument("action", type=click.Choice(["list", "add", "remove"]))
@click.option("--job-url", help="岗位URL")
@click.option("--title", default="", help="岗位名称")
@click.option("--company", default="", help="公司名")
@click.option("--id", "sid", type=int, help="shortlist ID")
def shortlist_cmd(action, job_url, title, company, sid):
    if action == "list":
        resp = client.get_shortlists()
        output.emit(output.ok_or_fail(resp, "shortlist"))
    elif action == "add":
        if not job_url:
            output.emit(output.fail("shortlist", "--job-url required"))
            return
        resp = client.add_shortlist(job_url, title, company)
        output.emit(output.ok_or_fail(resp, "shortlist"))
    elif action == "remove":
        if not sid:
            output.emit(output.fail("shortlist", "--id required"))
            return
        resp = client.remove_shortlist(sid)
        output.emit(output.ok_or_fail(resp, "shortlist"))


# ── 服务管理 ──
@main.command("server")
@click.option("--start", is_flag=True, help="启动后台服务")
@click.option("--stop", is_flag=True, help="停止后台服务（精确杀 boss_app 进程，不动其他 python）")
@click.option("--port", type=int, default=8010, help="服务端口")
def server_cmd(start, stop, port):
    import subprocess, os

    project_dir = os.path.dirname(os.path.dirname(__file__))
    if not os.path.exists(os.path.join(project_dir, "boss_app.py")):
        project_dir = os.environ.get("LAKEJOB_PROJECT", r"D:\lake\jiaoben\job\lakejobai-job-radar-main")

    if start:
        cmd = ["python", os.path.join(project_dir, "boss_app.py"), "--port", str(port)]
        subprocess.Popen(cmd, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000), cwd=project_dir)
        output.emit(output.ok("server", data={"status": "started", "url": f"https://127.0.0.1:{port}"}))
    elif stop:
        killed = _kill_boss_app()
        output.emit(output.ok("server", data={"status": "stopped", "killed": killed}))
    else:
        resp = client.status()
        if resp.is_error:
            output.emit(output.ok("server", data={"status": "not running"}))
        else:
            output.emit(output.ok("server", data={"status": "running"}))


@main.command("restart")
@click.option("--port", type=int, default=8010, help="端口号")
def restart_cmd(port):
    """杀旧进程 + 起新服务。Windows 用 wmic 精确杀，不动其他 python。"""
    import ssl, subprocess, os, time, urllib.request

    project_dir = os.path.dirname(os.path.dirname(__file__))
    if not os.path.exists(os.path.join(project_dir, "boss_app.py")):
        project_dir = os.environ.get("LAKEJOB_PROJECT", r"D:\lake\jiaoben\job\lakejobai-job-radar-main")

    boss_py = os.path.join(project_dir, "boss_app.py")
    if not os.path.exists(boss_py):
        output.emit(output.fail("restart", f"找不到 boss_app.py"))
        return

    killed = _kill_boss_app()
    if killed:
        click.echo(f"  killed {killed} process(es)")
    time.sleep(2)

    log_path = os.path.join(os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp", "boss_app.log")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    with open(log_path, "w", encoding="utf-8") as lf:
        subprocess.Popen(
            [sys.executable, boss_py, "--port", str(port)],
            stdout=lf,
            stderr=subprocess.STDOUT,
            cwd=project_dir,
            creationflags=flags,
        )

    time.sleep(5)
    try:
        urllib.request.urlopen(
            urllib.request.Request(f"https://127.0.0.1:{port}/api/health"),
            timeout=3,
            context=ssl._create_unverified_context(),
        )
        output.emit(output.ok("restart", data={"port": port, "url": f"https://127.0.0.1:{port}"}))
    except Exception:
        output.emit(
            output.ok(
                "restart",
                data={"port": port, "url": f"https://127.0.0.1:{port}", "note": "稍等再试"},
            )
        )


def _kill_boss_app():
    """精确杀死所有 boss_app.py 主进程（python 解释器执行 boss_app.py 的）。
    只匹配 cmdline 中包含 'boss_app.py' 的 python 进程，避免误杀任何包含 'boss_app' 字样的 shell。
    返回杀死数。
    """
    killed = 0
    try:
        import psutil  # type: ignore
    except Exception:
        psutil = None

    if psutil is not None:
        my_pid = os.getpid()
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                pid = p.info.get("pid")
                if pid == my_pid:
                    continue
                cmd = p.info.get("cmdline") or []
                if not isinstance(cmd, list):
                    continue
                name = (p.info.get("name") or "").lower()
                if "python" not in name and not any("python" in (a or "").lower() for a in cmd[:1]):
                    continue
                if not any("boss_app.py" in (a or "") for a in cmd):
                    continue
                p.kill()
                killed += 1
            except Exception:
                continue
        return killed

    # 兜底：用 wmic（旧 Windows 系统），但限定 commandline 必须含 boss_app.py
    import subprocess

    try:
        r = subprocess.run(
            "wmic process where \"name='python.exe' and commandline like '%%boss_app.py%%'\" get processid",
            capture_output=True,
            shell=True,
            text=True,
            timeout=10,
        )
        for line in r.stdout.split("\n"):
            line = line.strip()
            if line.isdigit() and int(line) != os.getpid():
                try:
                    subprocess.run(f"taskkill /F /PID {line}", capture_output=True, shell=True, timeout=5)
                    killed += 1
                except Exception:
                    pass
    except Exception:
        pass
    return killed


# ── 智能投递 ──
@main.command("smart-send")
@click.option("--keyword", default="", help="搜索关键词")
@click.option("--city", default="", help="城市")
@click.option("--greeting", default="", help="自定义招呼语")
@click.option("--yes", "-y", is_flag=True, help="跳过确认")
@click.option("--districts", default="", help="多区 code 列表，逗号分隔，如 440118,440113")
@click.option("--company-size", default="", help="多规模 code 列表，逗号分隔，如 302,303")
def smart_send_cmd(keyword, city, greeting, yes, districts, company_size):
    """智能投递：搜索→按公司分组→挑最高HR→批量投递。"""
    if not keyword:
        output.emit(output.fail("smart-send", "--keyword 必填"))
        return
    ds_list = [x.strip() for x in districts.split(",") if x.strip()] or None
    cs_list = [x.strip() for x in company_size.split(",") if x.strip()] or None
    try:
        resp = client.company_preview(
            keyword=keyword,
            city=city,
            districts=ds_list,
            company_size=cs_list,
        )
        data = resp.json() if not resp.is_error else None
    except Exception as e:
        output.emit(output.fail("smart-send", f"preview 失败: {e}"))
        return
    if resp.is_error or not data or not data.get("ok"):
        output.emit(output.fail("smart-send", f"preview 失败: {(data or {}).get('message', '')}"))
        return

    companies = data.get("companies") or []
    output.emit(output.ok("smart-send-preview", data={"total_companies": len(companies), "keyword": keyword}))

    targets = []
    for c in companies[:20]:
        if c.get("already_applied"):
            continue
        tj = c.get("target_job") or {}
        if not tj.get("url"):
            continue
        top = c.get("top_hr") or {}
        targets.append(
            {
                "company": c["company"],
                "job_url": tj["url"],
                "hr_name": top.get("name", ""),
                "hr_title": top.get("title", ""),
                "is_boss": top.get("is_boss", False),
                "boss_confidence": top.get("boss_confidence", ""),
            }
        )

    if not targets:
        output.emit(output.fail("smart-send", "没有可投递的公司"))
        return

    if not yes:
        click.echo(f"\n  共 {len(targets)} 家公司待投递：")
        for t in targets:
            boss_tag = ""
            if t.get("is_boss"):
                conf = {"high": "★老板", "medium": "疑似老板", "low": "可能老板?"}.get(
                    t.get("boss_confidence", ""), "疑似老板"
                )
                boss_tag = f"  [{conf}]"
            click.echo(f"    {t['company']}  →  {t.get('hr_name') or 'HR'} ({t.get('hr_title', '')}){boss_tag}")
        click.echo("\n  确认？[y/N] ", nl=False)
        try:
            ans = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            ans = "n"
        if ans not in ("y", "yes"):
            output.emit(output.ok("smart-send", data={"cancelled": True}))
            return

    resp2 = client.smart_send(company="", job_url="", targets=targets, confirm=True)
    result = output.ok_or_fail(resp2, "smart-send")
    try:
        payload = resp2.json()
        if isinstance(result.get("data"), dict) and isinstance(payload, dict):
            result["data"].update(payload)
    except Exception:
        pass
    output.emit(result)


if __name__ == "__main__":
    main()
