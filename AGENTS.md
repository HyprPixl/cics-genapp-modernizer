# Agent Log

## Progress Log
- Documented `LGAPOL01` (Add Policy COBOL program) and captured dependencies in the README and dependency graph store.
- Drafted documentation roadmap with sequencing and parallel work suggestions.
- Reviewed and documented `LGAPVS01` and `LGAPDB01`, noting VSAM and DB2 responsibilities plus shared error pathways.
- Completed Phase 1 coverage by documenting customer add/inquiry and policy inquiry front-ends with their backing services (`LGACUS01`, `LGACDB01`, `LGACVS01`, `LGICUS01`, `LGICDB01`, `LGIPOL01`, `LGIPDB01`).
- Completed Phase 2 coverage by inventorying core data services (`LGACDB02`, `LGUCDB01`, `LGUCVS01`, `LGUPDB01`, `LGUPVS01`, `LGSTSQ`) and recording their responsibilities and dependencies.
- Completed Phase 3 coverage by summarizing shared copybooks (`LGCMAREA`, `LGPOLICY`, `POLLOOK`, `POLLOO2`) and mapset `SSMAP.bms` in the central documentation.
- Completed Phase 4 coverage by cataloguing operational assets (JCL catalog, REXX utilities, `install.sh`) and their roles in environment provisioning.
- Completed Phase 5 coverage by documenting data seeds, WSIM simulation scripts, and the CICS event binding configuration.

## Dependency Notes
- `LGAPOL01` depends on `LGAPDB01` (database insert logic), `LGSTSQ` (TDQ logging helper), and the `LGCMAREA` copybook.
- `LGAPVS01` writes to VSAM cluster `KSDSPOLY`, consumes `LGCMAREA`, and logs via `LGSTSQ`.
- `LGAPDB01` relies on DB2 tables (`POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`, `COMMERCIAL`), invokes `LGAPVS01`, and uses `LGPOLICY`/`LGCMAREA` copybooks plus `LGSTSQ` for diagnostics.
- `LGACUS01` fronts customer creation and links to `LGACDB01`, which in turn invokes `LGACVS01` and `LGACDB02`; VSAM cluster `KSDSCUST` persists the mirror image.
- `LGICUS01` delegates to `LGICDB01` for customer lookups; `LGIPOL01` couples to `LGIPDB01` for policy and extension retrievals.
- Data service additions: `LGACDB02` writes to DB2 table `CUSTOMER_SECURE`, `LGUCDB01`/`LGUCVS01` keep DB2 and VSAM customer records synchronized, `LGUPDB01`/`LGUPVS01` coordinate policy updates across DB2 and VSAM, and `LGSTSQ` remains the centralized logging sink.
- Shared asset additions: copybooks (`LGCMAREA`, `LGPOLICY`, `POLLOOK`, `POLLOO2`) and `SSMAP.bms` mapset are now catalogued with purposes to guide future refactors.
- Ops tooling: `cobol.jcl` encapsulates the COBOL/DB2 compile pipeline, `cust1.rexx`/`mac1.rexx` apply site-specific variables, and `install.sh` mirrors content into `${USER}.GENAPP` datasets via USS.
- Data & simulation assets: dataset seeds align with VSAM layouts, WSIM scripts automate end-to-end scenario playback, and `Transaction_Counters.evbind` captures runtime metrics from commarea headers.

## Tooling
- Dependency graph helper lives at `tools/dep_graph.py`; default store is `dependency_graph.json`.
- Add/update a node: `./tools/dep_graph.py add-node <NAME> --type <category> --description "..." --depends-on dep1 dep2`.
- Create an edge later: `./tools/dep_graph.py add-edge <SOURCE> <TARGET>`.
- Inspect a node: `./tools/dep_graph.py show <NAME> --include-dependents`.
- List nodes (optionally by type): `./tools/dep_graph.py list --type cobol`.
- Review dependents of a component: `./tools/dep_graph.py dependents <NAME>`.

## Work Sequencing
- **Phase 1 – Core Transactions (serial):** Continue through customer and policy front-end programs (`LGAPOL01`, `LGAPVS01`, `LGACUS01`, etc.), pairing each with its backing DB module so request/response flows stay consistent. ✅ Completed.
- **Phase 2 – Data Services (serial):** Document batch/database utilities (`LGAPDB01`, `LGDPDB01`, `LGIPDB01`, `LGUCDB01`) and shared logging (`LGSTSQ`) once their callers are understood. ✅ Completed.
- **Phase 3 – Shared Assets (parallel):** Tackle copybooks (`LGCMAREA`, `POLLOOK`, `POLLOO2`, `SOA*`) and BMS maps (`SSMAP.bms`) alongside transaction work; these can be owned by a separate teammate with ongoing updates. ✅ Completed (initial pass).
- **Phase 4 – Ops & Automation (parallel):** While COBOL review continues, another stream can inventory JCL in `base/cntl/`, REXX execs, and `install.sh`, cross-linking jobs to program compile/deploy steps. ✅ Completed (summary captured).
- **Phase 5 – Data & Simulation (parallel):** In parallel with ops review, analyze `base/data/` datasets and `base/wsim/` scripts, documenting how they support test scenarios and customer journeys. ✅ Completed.

## Parallelization Notes
- Pair front-end and back-end COBOL modules in the same lane to avoid re-reading shared commareas.
- Assign separate owners for shared copybooks/maps and for infrastructure artifacts (JCL/REXX/data) so updates proceed without blocking the core transaction walkthrough.
- Revisit the dependency graph after each phase to confirm cross-stream updates stay synchronized.
