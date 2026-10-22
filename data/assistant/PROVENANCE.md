# Assistant capability policy

`openai-capabilities.json` is edi product policy, checked against the cited official OpenAI model/deployment
references on 2026-10-15. It declares capabilities for exact model IDs; it is not an account entitlement list,
measured capacity or provider `/v1/models` response. The account catalog remains authoritative for availability.
Unknown IDs require a reviewed mapping before assistant use. Effort labels are app-owned text; undocumented
catalog effort fields are ignored. The same embedded Qt-free resource serves core and native validation.
