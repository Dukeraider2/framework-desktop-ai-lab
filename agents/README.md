# Founding agent identities

The registry and individual Hermes profile distributions define durable organizational identities. Each distribution has one canonical `SOUL.md`; install it as an independent Hermes profile with `hermes profile install ./agents/profiles/<profile>`. The profiles intentionally ship no model, credentials, MCP servers, WhatsApp channels, or permission grants. Their baseline config enables only `todo`, `memory`, `session_search`, and `clarify`; it excludes terminal, browser, and delegation tools. Model/provider configuration is managed separately for each profile, so replacing a model does not replace identity. Do not clone the WhatsApp-enabled `default` profile or copy its credentials into agent profiles.

Hermes loads an installed profile's `SOUL.md` as its primary identity. After deployment, verify the loaded file using `hermes -p <profile> chat` and `/context`. These repository distributions have not been installed into the current Hermes home. Project knowledge and work history remain in GitHub, not conversational memory alone.

Identity names are fictional AI personas inspired by public characteristics and intellectual contributions. They are not the people who inspired them. All seven profiles inherit the same intellectual-independence and evidence requirements. Mentioning or assigning an agent is not permission to act.

Operational authorization, model selection, credentials, WhatsApp access, and toolsets are local administrator-managed configuration and must be reviewed independently. Do not place secrets or personal identifiers in this directory.
