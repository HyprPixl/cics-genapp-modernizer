# Agent Log

## Progress Log
- Documented `LGAPOL01` (Add Policy COBOL program) and captured dependencies in the README and dependency graph store.
- Drafted documentation roadmap with sequencing and parallel work suggestions.
- Reviewed and documented `LGAPVS01` and `LGAPDB01`, noting VSAM and DB2 responsibilities plus shared error pathways.
- **PHASE 1 COMPLETE:** Documented all core transaction front-end programs and their immediate dependencies:
  - Customer operations: `LGACUS01` (add), `LGICUS01` (inquire), `LGUCUS01` (update) with backing services `LGACDB01`, `LGACVS01`
  - Policy operations: `LGAPOL01` (add), `LGIPOL01` (inquire), `LGUPOL01` (update), `LGDPOL01` (delete) with backing services `LGAPDB01`, `LGAPVS01`
  - All front-end programs follow consistent patterns: commarea validation, request ID checking, backend delegation, error logging via `LGSTSQ`

## Dependency Notes
- `LGAPOL01` depends on `LGAPDB01` (database insert logic), `LGSTSQ` (TDQ logging helper), and the `LGCMAREA` copybook.
- `LGAPVS01` writes to VSAM cluster `KSDSPOLY`, consumes `LGCMAREA`, and logs via `LGSTSQ`.
- `LGAPDB01` relies on DB2 tables (`POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`, `COMMERCIAL`), invokes `LGAPVS01`, and uses `LGPOLICY`/`LGCMAREA` copybooks plus `LGSTSQ` for diagnostics.
- Customer front-ends (`LGACUS01`, `LGICUS01`, `LGUCUS01`) all depend on corresponding DB backends (`LGACDB01`, `LGICDB01`, `LGUCDB01`) and shared infrastructure (`LGSTSQ`, `LGCMAREA`).
- Policy front-ends (`LGAPOL01`, `LGIPOL01`, `LGUPOL01`, `LGDPOL01`) follow similar patterns with DB backends (`LGAPDB01`, `LGIPDB01`, `LGUPDB01`, `LGDPDB01`).
- All transaction programs share error logging through `LGSTSQ` and use `LGCMAREA` for consistent commarea structure.

## Tooling
- Dependency graph helper lives at `tools/dep_graph.py`; default store is `dependency_graph.json`.
- Add/update a node: `./tools/dep_graph.py add-node <NAME> --type <category> --description "..." --depends-on dep1 dep2`.
- Create an edge later: `./tools/dep_graph.py add-edge <SOURCE> <TARGET>`.
- Inspect a node: `./tools/dep_graph.py show <NAME> --include-dependents`.
- List nodes (optionally by type): `./tools/dep_graph.py list --type cobol`.
- Review dependents of a component: `./tools/dep_graph.py dependents <NAME>`.

## Agent Task Assignments

### Agent 1 Task: Core Transactions & Data Services (Serial Work)
**Priority:** Critical Path - Must be completed sequentially
**Focus:** Transaction programs and their backing database services

**Phase 1 – Core Transactions:**
- Continue through customer and policy front-end programs (`LGAPOL01`, `LGAPVS01`, `LGACUS01`, etc.)
- Pair each front-end with its backing DB module so request/response flows stay consistent
- Document transaction patterns: commarea validation, request ID checking, backend delegation

**Phase 2 – Data Services:**
- Document batch/database utilities (`LGAPDB01`, `LGDPDB01`, `LGIPDB01`, `LGUCDB01`)
- Document shared logging service (`LGSTSQ`) once its callers are understood
- Map DB2 table relationships and VSAM cluster dependencies

### Agent 2 Task: Shared Assets (Parallel Work)
**Priority:** High - Can run in parallel with Agent 1
**Focus:** Copybooks, BMS maps, and shared data structures

**Responsibilities:**
- Document copybooks (`LGCMAREA`, `POLLOOK`, `POLLOO2`, `SOA*`) 
- Analyze BMS maps (`SSMAP.bms`) and screen flow definitions
- Maintain cross-references as Agent 1 discovers usage patterns
- Update dependency graph with shared asset relationships

### Agent 3 Task: Ops & Automation (Parallel Work)  
**Priority:** Medium - Can run in parallel with other agents
**Focus:** Build, deployment, and operational tooling

**Responsibilities:**
- Inventory JCL members in `base/cntl/` and map to functions (compile, bind, housekeeping)
- Document REXX executives in `base/exec/` for build and operations automation
- Analyze `install.sh` script for deployment procedures and dataset allocation
- Cross-link JCL jobs to program compile/deploy steps discovered by Agent 1

### Agent 4 Task: Data & Simulation (Parallel Work)
**Priority:** Medium - Can run in parallel with other agents  
**Focus:** Test data, simulation scripts, and customer journey scenarios

**Responsibilities:**
- Analyze sample datasets in `base/data/` (`ksdscust.txt`, `ksdspoly.txt`)
- Document workstation simulator flows in `base/wsim/` scripts
- Map simulation scenarios to transaction programs being documented by Agent 1
- Document customer journey test scenarios and data relationships

## Agent Coordination Notes
- **Agent 1** (Core Transactions) drives the critical path - other agents should sync with their findings
- **Agent 2** (Shared Assets) should pair front-end and back-end COBOL modules in the same review cycle to avoid re-reading shared commareas
- **Agents 2, 3, 4** work in parallel streams for copybooks/maps, infrastructure artifacts (JCL/REXX/data), and simulation assets
- All agents should update the dependency graph after each work session to keep cross-stream updates synchronized
- Regular sync points recommended between agents to ensure discoveries are shared (especially between Agent 1 and Agent 2)
