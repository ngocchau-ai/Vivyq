# Capability Distillation Protocol

Dùng khi một repo/tool chuyên dụng có capability cần thiết nhưng không nên cài toàn bộ.

## Quy trình

1. Xác định capability gap hẹp.
2. Khảo sát repo: README, entrypoint, dependency, license, auth, network, filesystem.
3. Security review: secrets, remote code download, unexpected network, writes outside workspace.
4. Chọn phần cần giữ:
   - workflow/prompt → Skill
   - deterministic script/CLI → Tool
   - external service integration → Connector/MCP
   - bundle → Plugin
5. Viết host adapter theo tài liệu hiện hành của host.
6. Ghim dependency/version khi phù hợp.
7. Tạo 3–5 golden tasks.
8. Test trong sandbox.
9. Ghi source/commit/license/test/rollback vào registry.
10. Install vào host thật chỉ khi risk policy cho phép.

## Cấu trúc gợi ý

```text
distilled-<name>/
  SOURCE.md
  skill/
  tools/
  adapters/
  tests/
  CHANGELOG.md
```
