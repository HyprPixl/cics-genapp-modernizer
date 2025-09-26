# Agent Log

## Progress Log
- Documented `LGAPOL01` (Add Policy COBOL program) and captured dependencies in the README and dependency graph store.
- Drafted documentation roadmap with sequencing and parallel work suggestions.
- Reviewed and documented `LGAPVS01` and `LGAPDB01`, noting VSAM and DB2 responsibilities plus shared error pathways.
- **PHASE 1 COMPLETE:** Documented all core transaction front-end programs and their immediate dependencies:
  - Customer operations: `LGACUS01` (add), `LGICUS01` (inquire), `LGUCUS01` (update) with backing services `LGACDB01`, `LGACVS01`
  - Policy operations: `LGAPOL01` (add), `LGIPOL01` (inquire), `LGUPOL01` (update), `LGDPOL01` (delete) with backing services `LGAPDB01`, `LGAPVS01`
  - All front-end programs follow consistent patterns: commarea validation, request ID checking, backend delegation, error logging via `LGSTSQ`
- **PHASE 2 COMPLETE:** Documented all data services (batch/database utilities) and shared logging infrastructure:
  - Shared logging: `LGSTSQ` - centralized TDQ/TSQ diagnostic logging service
  - Policy data services: `LGDPDB01` (delete), `LGIPDB01` (inquire with complex cursors), `LGUPDB01` (update with locking)
  - Customer data services: `LGUCDB01` (update), `LGICDB01` (inquire)
  - All data services follow consistent error handling, use `LGSTSQ` for diagnostics, and coordinate DB2/VSAM synchronization

## Dependency Notes
- `LGAPOL01` depends on `LGAPDB01` (database insert logic), `LGSTSQ` (TDQ logging helper), and the `LGCMAREA` copybook.
- `LGAPVS01` writes to VSAM cluster `KSDSPOLY`, consumes `LGCMAREA`, and logs via `LGSTSQ`.
- `LGAPDB01` relies on DB2 tables (`POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`, `COMMERCIAL`), invokes `LGAPVS01`, and uses `LGPOLICY`/`LGCMAREA` copybooks plus `LGSTSQ` for diagnostics.
- Customer front-ends (`LGACUS01`, `LGICUS01`, `LGUCUS01`) all depend on corresponding DB backends (`LGACDB01`, `LGICDB01`, `LGUCDB01`) and shared infrastructure (`LGSTSQ`, `LGCMAREA`).
- Policy front-ends (`LGAPOL01`, `LGIPOL01`, `LGUPOL01`, `LGDPOL01`) follow similar patterns with DB backends (`LGAPDB01`, `LGIPDB01`, `LGUPDB01`, `LGDPDB01`).
- All transaction programs share error logging through `LGSTSQ` and use `LGCMAREA` for consistent commarea structure.
- **Phase 2 Data Services:** All DB backends depend on their corresponding VSAM sync programs (`LGAPVS01`, `LGDPVS01`, `LGUCVS01`, `LGUPVS01`) and share common dependencies on `LGPOLICY` copybook for DB2 field definitions.
- `LGSTSQ` is the foundation logging service used by all other programs - supports both programmatic (LINK) and terminal (transaction) invocation modes.
- Complex inquiry services (`LGIPDB01`) use scroll cursors and handle multiple policy types, while simpler services (`LGICDB01`) use single-row SELECTs.
- Update services (`LGUCDB01`, `LGUPDB01`) implement optimistic concurrency control and coordinate dual persistence (DB2 + VSAM).

## Tooling
- Dependency graph helper lives at `tools/dep_graph.py`; default store is `dependency_graph.json`.
- Add/update a node: `./tools/dep_graph.py add-node <NAME> --type <category> --description "..." --depends-on dep1 dep2`.
- Create an edge later: `./tools/dep_graph.py add-edge <SOURCE> <TARGET>`.
- Inspect a node: `./tools/dep_graph.py show <NAME> --include-dependents`.
- List nodes (optionally by type): `./tools/dep_graph.py list --type cobol`.
- Review dependents of a component: `./tools/dep_graph.py dependents <NAME>`.

## Work Sequencing
- **Phase 1 – Core Transactions (serial): ✅ COMPLETE** - Documented all customer and policy front-end programs with their backing DB modules, maintaining consistent request/response flows.
- **Phase 2 – Data Services (serial): ✅ COMPLETE** - Documented batch/database utilities (`LGAPDB01`, `LGDPDB01`, `LGIPDB01`, `LGUCDB01`, `LGICDB01`, `LGUPDB01`) and shared logging (`LGSTSQ`) with comprehensive dependency mapping.
- **Phase 3 – Shared Assets (parallel):** Tackle copybooks (`LGCMAREA`, `POLLOOK`, `POLLOO2`, `SOA*`) and BMS maps (`SSMAP.bms`) alongside transaction work; can be owned by a separate teammate with ongoing updates.
- **Phase 4 – Ops & Automation (parallel):** While COBOL review continues, another stream can inventory JCL in `base/cntl/`, REXX execs, and `install.sh`, cross-linking jobs to program compile/deploy steps.
- **Phase 5 – Data & Simulation (parallel):** In parallel with ops review, analyze `base/data/` datasets and `base/wsim/` scripts, documenting how they support test scenarios and customer journeys.

## Parallelization Notes
- Pair front-end and back-end COBOL modules in the same lane to avoid re-reading shared commareas.
- Assign separate owners for shared copybooks/maps and for infrastructure artifacts (JCL/REXX/data) so updates proceed without blocking the core transaction walkthrough.
- Revisit the dependency graph after each phase to confirm cross-stream updates stay synchronized.
