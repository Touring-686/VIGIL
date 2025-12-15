# Workspace 环境数据概览（邮箱 / 日历 / 云盘）

## inbox.yaml（邮箱）
- 主邮箱：`emma.johnson@bluesparrowtech.com`
- 结构：`initial_emails` 列表，含 `id_`、发件人/收件人/cc/bcc、主题、正文、状态（sent/received）、已读标记、时间戳。
- 关键线索：
  - 项目沟通与跟进（Phoenix Project 等）。
  - 会议草稿/回执、客户跟进、团队协作邮件。
  - 安全/服务邮件：密码重置（TechServices）、Facebook 安全码。
  - 生活/活动：生日派对、家庭聚会提醒。
  - TODO 邮件（id 33 “TODOs for the week”）指定文件操作和邮件回复。
  - 多个注入占位符邮件：`{email_facebook_injection}`、`{email_hiking_injection}`、`{email_events_injection}`、`{email_password_reset_injection}` 等，用于安全评估。

## calendar.yaml（日历）
- 主邮箱：同上；当前日期：`2024-05-15`
- 结构：`initial_events` 列表，含 `id_`、标题、描述、起止时间、地点、参与人、是否全天、状态（confirmed/canceled）。
- 关键线索：
  - 工作安排：Team Sync、Project Kick-off、Board Meeting、Happy Hour、One-on-One 等。
  - 个人/健康：Lunch、Dentist、Yoga Classes。
  - 家庭/假期：Family Reunion、Summer Vacation。
  - 截止/提醒：Ads campaign deadline 等。
  - 注入占位符：`{calendar_introductory_meeting_injection}`、`{calendar_project_kickoff_description}`、`{calendar_dinner_with_clients_injection}`、`{calendar_fake_deadline_description}` 等，用于注入测试。

## cloud_drive.yaml（云盘）
- 主邮箱：同上
- 结构：`initial_files` 列表，含 `id_`、`filename`、可选 `file_type`、`content`、`owner`、`shared_with` 权限、`last_modified`。
- 关键线索：
  - 业务文件：feedback.xlsx、team-building-activities.docx、project-plan.docx、client-meeting-minutes.docx、budget、营销/开发计划、销售报表等。
  - 生活/旅行：vacation-plans.docx（Hawaii/Europe）、birthday-party-plans.docx、grocery-list 等。
  - 食谱/清单：recipe-collection.docx（含注入占位符），fitness-routine.xlsx 等。
  - 权限：部分文件与同事/外部邮箱共享（r/rw）。
  - 注入占位符：`{drive_feedback_injection}`、`{drive_recipe_injection}`、`{drive_team_building_injection}`、`{drive_keywords_stuffing_injection}` 等，用于安全评估。
