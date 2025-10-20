# Repo Map After PTY Static De-dupe (2025-10-20)

Below is an abbreviated tree (depth 2) for verification:

```
.
├── .env
├── .env.example
├── .github
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   └── workflows
├── .gitignore
├── .gitmodules
├── .pre-commit-config.yaml
├── .test-vterm.sock
├── .x-user
│   ├── 4botbsc
│   ├── clitest
│   ├── Default
│   └── Profile 13
├── 4BOT_SYSTEM_DOCUMENTATION.md
├── apps
│   ├── __init__.py
│   └── cz
├── artifacts
│   ├── auth_x_netscape.json
│   ├── har
│   ├── html
│   ├── logs
│   ├── misc
│   ├── results
│   ├── screens
│   ├── state
│   ├── test_outputs
│   └── traces
├── auth
│   ├── 4botbsc
│   ├── bar
│   ├── foo
│   ├── Profile 13
│   └── storageState.json
├── auth_data
│   ├── headless_session_screenshot.png
│   ├── x_cookies_netscape.txt
│   ├── x_cookies.json
│   ├── x_tokens.env
│   ├── x_tokens.json
│   └── x_tokens.txt
├── bin
│   ├── convert_netscape_to_json.py
│   ├── cz_wall_post.py
│   ├── dev-setup.sh
│   ├── generate_cz_reply_drafts.py
│   ├── launchd
│   ├── start_cz_pipeline.sh
│   ├── token_audit.py
│   ├── wait_then_reply.py
│   └── webkit_login_export.py
├── chrome_profiles
│   ├── cookies
│   ├── profile_mapper.py
│   └── profile_mapping.json
├── CLAUDE.md
├── config
│   ├── active_profile
│   ├── monitor
│   └── profiles
├── Docs
│   ├── 4Bot Tweets.md
│   ├── architecture
│   ├── available_tweets.md
│   ├── DEVELOPER_PTYTERM.md
│   ├── GitHub X Automation Browser Wrappers.md
│   ├── launchd
│   ├── status
│   └── TEST_COVERAGE_REPORT.md
├── dual_monitor_logs
│   ├── dual_monitor_report_20251016_190130.json
│   ├── feed_20251016_190130.log
│   └── notifications_20251016_190130.log
├── EVENT_MONITORING.md
├── logs
│   ├── 4botbsc
│   ├── auto_responder_cz.log
│   ├── auto_responder.out
│   ├── cz_auto_20251016_230114.log
│   ├── cz_auto_20251016_230502.log
│   ├── cz_auto_20251016_230715.log
│   ├── cz_auto_20251016_230919.log
│   ├── cz_auto_20251017_010202.log
│   ├── cz_batch_20251016_headless.log
│   ├── cz_batch_20251016.log
│   ├── cz_batch_log.json
│   ├── cz_daemon
│   ├── cz_notification_monitor.log
│   ├── cz_posts.out
│   ├── cz_reply_poster.log
│   ├── event_monitor.log
│   ├── fud_reply_cz_persist.log
│   ├── fud_reply_cz.log
│   ├── headless_batch
│   ├── monitor
│   ├── monitor_log_20251016_173714.log
│   ├── notification_parser.log
│   ├── pending_reply_20251017_022441.log
│   ├── pending_reply_20251017_022522.log
│   ├── pending_reply_20251017_022626.log
│   ├── safari_login.log
│   ├── session_bootstrap_20251017_022819.log
│   ├── sso_webkit_20251017_022441.log
│   ├── test_monitor_output.log
│   ├── vterm_http.log
│   ├── vterm_http.out
│   └── vterm_proxy.log
├── Makefile
├── notes.md
├── notification_json_logs
│   ├── notifications_20251016_191140.json
│   ├── notifications_20251016_191140.log
│   ├── notifications_20251016_191806.json
│   └── notifications_20251016_191806.txt
├── notification_logs
│   ├── notification_report_20251016_185934.json
│   └── notifications_20251016_185730.log
├── playbooks
│   ├── cz_batch_2025-10-16.json
│   └── sample.json
├── prompts
│   └── persona_cz.system.md
├── pyproject.toml
├── RABBITMQ_SETUP.md
├── requirements-ptyterm.txt
├── requirements.txt
├── schedules
│   └── sample.json
├── scripts
│   ├── auth
│   ├── hooks
│   ├── launch
│   ├── manual
│   ├── monitor
│   ├── notification
│   ├── orchestrator
│   ├── rabbitmq
│   └── shell
├── server_test.err
├── server_test.pid
├── server.err
├── server.pid
├── submodules
│   └── ptyterm
├── tests
│   ├── base_test_fixture.py
│   ├── conftest.py
│   ├── fixtures
│   ├── mock_factories.py
│   ├── test_active_profile.py
│   ├── test_cli_profiles.py
│   ├── test_collect_only.py
│   ├── test_cookie_manager.py
│   ├── test_daily_index_cli.py
│   ├── test_deps_cli.py
│   ├── test_deps_remote_cli.py
│   ├── test_deps_set_urls_cli.py
│   ├── test_health_imports.py
│   ├── test_health_strict.py
│   ├── test_launchd_renderer_smoke.py
│   ├── test_no_abs_user_paths_py.py
│   ├── test_no_hardcoded_storage_paths_py.py
│   ├── test_no_vterm_vendor.py
│   ├── test_notification_parser.py
│   ├── test_paths_cli_json.py
│   ├── test_paths_cli.py
│   ├── test_paths_diff_cli.py
│   ├── test_paths_doctor_cli_json.py
│   ├── test_paths_doctor_cli.py
│   ├── test_paths_env_cli.py
│   ├── test_paths_export_cli.py
│   ├── test_paths_init_cli.py
│   ├── test_paths_markdown_cli.py
│   ├── test_paths_validate_cli.py
│   ├── test_playbook_schema.py
│   ├── test_profiles_helpers.py
│   ├── test_profiles.py
│   ├── test_ptyterm_client_queue.py
│   ├── test_ptyterm_queue_cli.py
│   ├── test_rabbitmq_message_flow.py
│   ├── test_rate_limiter_basic.py
│   ├── test_redact_and_secrets.py
│   ├── test_repo_hygiene.py
│   ├── test_report_aggregate.py
│   ├── test_report_gallery_cli.py
│   ├── test_report_health_guardrails.py
│   ├── test_report_health_scheduler.py
│   ├── test_report_html_image_relpath.py
│   ├── test_report_manifest_cli.py
│   ├── test_report_scan_secrets_cli.py
│   ├── test_report_version_cli.py
│   ├── test_results_paths.py
│   ├── test_results_prune_cli.py
│   ├── test_results_rebuild_index_cli.py
│   ├── test_safety_eval.py
│   ├── test_safety.py
│   ├── test_scheduler_fair.py
│   ├── test_site_cli_strict.py
│   ├── test_site_cli.py
│   ├── test_site_gallery_integration.py
│   ├── test_site_proxies.py
│   ├── test_site_secrets_integration.py
│   ├── test_state_json_shape.py
│   ├── test_status_index_extra.py
│   ├── test_status_index_md.py
│   ├── test_status_index_paths.py
│   ├── test_status_index_results_links.py
│   ├── test_status_index.py
│   ├── test_vterm_audit_report.py
│   ├── test_vterm_cli_queue.py
│   ├── test_vterm_cli.py
│   ├── test_vterm_context.py
│   ├── test_vterm_daemon.py
│   ├── test_vterm_http_admin_shutdown.py
│   ├── test_vterm_http_auth.py
│   ├── test_vterm_http_console.py
│   ├── test_vterm_http_latency_histogram.py
│   ├── test_vterm_http_metrics.py
│   ├── test_vterm_http_parallel_runs.py
│   ├── test_vterm_http_queue.py
│   ├── test_vterm_http_rate.py
│   ├── test_vterm_http_tail_ws_replay.py
│   ├── test_vterm_http_version.py
│   ├── test_vterm_http_ws.py
│   ├── test_vterm_http.py
│   ├── test_vterm_policy_check_cli.py
│   ├── test_vterm_server.py
│   ├── test_vterm_xbot.py
│   ├── test_vterm.py
│   └── test_wrapper_hygiene.py
└── xbot
    ├── __init__.py
    ├── artifacts.py
    ├── audit_report.py
    ├── auto_responder.py
    ├── browser.py
    ├── cli.py
    ├── compose.py
    ├── config.py
    ├── cookies.py
    ├── cz_reply.py
    ├── errors.py
    ├── event_interceptor.py
    ├── facade.py
    ├── flows
    ├── health.py
    ├── human.py
    ├── logging_setup.py
    ├── media.py
    ├── monitor_integration.py
    ├── notification_json_parser.py
    ├── notifications.py
    ├── notify_to_rmq.py
    ├── orchestrator_sim.py
    ├── playbook.py
    ├── profiles.py
    ├── prompts.py
    ├── rabbitmq_manager.py
    ├── ratelimit.py
    ├── repo_report.py
    ├── report_aggregate.py
    ├── report_health.py
    ├── report_html.py
    ├── report.py
    ├── results.py
    ├── safety.py
    ├── scheduler_fair.py
    ├── scheduler.py
    ├── secrets.py
    ├── selectors.py
    ├── state.py
    ├── static
    ├── telemetry.py
    ├── utils.py
    ├── vterm_client.py
    ├── vterm_http.py
    ├── vterm.py
    ├── vtermd.py
    └── waits.py

65 directories, 217 files

```

Removed:
- xbot/static/vterm_console.html
- xbot/static/vterm_console.js

Single source of truth for PTY/VTerm implementation:
- submodules/ptyterm/ptyterm/*.py
- submodules/ptyterm/ptyterm/static/*

4bot only re-exports ptyterm symbols via:
- xbot/vterm.py, xbot/vtermd.py, xbot/vterm_client.py, xbot/vterm_http.py

