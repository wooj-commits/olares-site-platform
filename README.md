# olares-site-platform

Reusable native Olares hosting for small sites: **Next.js 15 single container**, Better Auth, system Postgres, Market MinIO.

| Piece | Location |
|-------|----------|
| Demo app | `apps/demo` |
| Installable chart | `chart/olaresdemo` |
| Copy-paste chart template | `chart/site-template` |
| New site steps | `docs/new-site-checklist.md` |
| Image | `ghcr.io/wooj-commits/olares-site-platform` (public) |

## Stack (chosen)

**Next.js 15 (App Router) + Better Auth + `pg` + AWS SDK S3 client**, one Docker image (`output: "standalone"`). No separate API service.

## Demo URL (after install)

`https://web.olaresdemo.woojinc1205.olares.com`

## OAuth callbacks

- `https://web.olaresdemo.woojinc1205.olares.com/api/auth/callback/google`
- `https://web.olaresdemo.woojinc1205.olares.com/api/auth/callback/github`

Credentials go in Olares **Settings → Applications → Olares Demo** (`GOOGLE_*` / `GITHUB_*`). Leave empty to keep social login disabled.

## Auto-deploy routine (create in Grok Bot — do not invent secrets)

**Trigger (GitHub):**

```json
{
  "type": "github",
  "repo": "wooj-commits/olares-site-platform",
  "events": ["ci-passed"],
  "ciBranch": "main"
}
```

**Routine prompt (paste as-is):**

```
When CI passes on main for wooj-commits/olares-site-platform, non-destructively upgrade the Olares demo app olaresdemo on woojinc1205: download the latest chart .tgz release asset (or workflow artifact), upload/upgrade via Market or olares-cli without uninstalling other apps or wiping Postgres/MinIO data, wait until the app is running, then hit https://web.olaresdemo.woojinc1205.olares.com/api/health and report status. If olares-cli needs profile login or Market auth, pause and ask Woojin in this chat. Never print or commit secrets. Deliver the result to the user in this chat; if nothing changed beyond a green build already deployed, say so briefly.
```

## License

Apache-2.0
