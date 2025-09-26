# Agent Log

## Progress Log
- Documented `LGAPOL01` (Add Policy COBOL program) and captured dependencies in the README and dependency graph store.
- Drafted documentation roadmap with sequencing and parallel work suggestions.
- Reviewed and documented `LGAPVS01` and `LGAPDB01`, noting VSAM and DB2 responsibilities plus shared error pathways.
- **PHASE 1 COMPLETE:** Documented all core transaction front-end programs and their immediate dependencies:
  - Customer operations: `LGACUS01` (add), `LGICUS01` (inquire), `LGUCUS01` (update) with backing services `LGACDB01`, `LGACVS01`
  - Policy operations: `LGAPOL01` (add), `LGIPOL01` (inquire), `LGUPOL01` (update), `LGDPOL01` (delete) with backing services `LGAPDB01`, `LGAPVS01`
  - All front-end programs follow consistent patterns: commarea validation, request ID checking, backend delegation, error logging via `LGSTSQ`
- **PHASE 2 COMPLETE:** Documented all remaining database backend services and their data dependencies:
  - Policy database services: `LGDPDB01` (delete), `LGIPDB01` (inquire), `LGUPDB01` (update) with corresponding VSAM sync services
  - Customer database services: `LGICDB01` (inquire), `LGUCDB01` (update), `LGACDB02` (security) with VSAM coordination
  - All database services follow consistent patterns: DB2 operations, VSAM synchronization, comprehensive error handling via `LGSTSQ`
- **PHASE 3 TASK 4 COMPLETE:** Documented SOA data copybooks for web service integration:
  - `SOAVCII`/`SOAVCIO`: Customer inquiry web service input/output commareas for LGICVS01 VSAM lookups
  - `SOAVPII`/`SOAVPIO`: Policy validation web service input/output commareas for LGIPVS01 policy validation
  - All SOA copybooks support CICS Language Structure to WSDL (LS2WS) conversion for web service endpoints
  - Integration with CICS web service infrastructure and JCL automation (wsavc01.jcl, wsavp01.jcl)

## Dependency Notes
- `LGAPOL01` depends on `LGAPDB01` (database insert logic), `LGSTSQ` (TDQ logging helper), and the `LGCMAREA` copybook.
- `LGAPVS01` writes to VSAM cluster `KSDSPOLY`, consumes `LGCMAREA`, and logs via `LGSTSQ`.
- `LGAPDB01` relies on DB2 tables (`POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`, `COMMERCIAL`), invokes `LGAPVS01`, and uses `LGPOLICY`/`LGCMAREA` copybooks plus `LGSTSQ` for diagnostics.
- Customer front-ends (`LGACUS01`, `LGICUS01`, `LGUCUS01`) all depend on corresponding DB backends (`LGACDB01`, `LGICDB01`, `LGUCDB01`) and shared infrastructure (`LGSTSQ`, `LGCMAREA`).
- Policy front-ends (`LGAPOL01`, `LGIPOL01`, `LGUPOL01`, `LGDPOL01`) follow similar patterns with DB backends (`LGAPDB01`, `LGIPDB01`, `LGUPDB01`, `LGDPDB01`).
- All transaction programs share error logging through `LGSTSQ` and use `LGCMAREA` for consistent commarea structure.
- **Phase 2 Database Service Dependencies:** All database backend services (`*DB01`) depend on DB2 tables, corresponding VSAM sync services (`*VS01`), shared copybooks (`LGCMAREA`, `LGPOLICY`), and error logging (`LGSTSQ`).
- **Database-VSAM Synchronization Pattern:** Policy services sync to `KSDSPOLY`, customer services sync to `KSDSCUST`; all VSAM services depend on `LGCMAREA` and `LGSTSQ`.
- **Customer Security Integration:** `LGACDB01` coordinates with `LGACDB02` for secure credential management in `CUSTOMER_SECURE` table.
- **SOA Web Service Integration:** `LGICVS01` uses `SOAVCII`/`SOAVCIO` for customer inquiries, `LGIPVS01` uses `SOAVPII`/`SOAVPIO` for policy validation; all support CICS LS2WS conversion for web service endpoints via JCL automation (`wsavc01.jcl`, `wsavp01.jcl`).

## Tooling
- Dependency graph helper lives at `tools/dep_graph.py`; default store is `dependency_graph.json`.
- Add/update a node: `./tools/dep_graph.py add-node <NAME> --type <category> --description "..." --depends-on dep1 dep2`.
- Create an edge later: `./tools/dep_graph.py add-edge <SOURCE> <TARGET>`.
- Inspect a node: `./tools/dep_graph.py show <NAME> --include-dependents`.
- List nodes (optionally by type): `./tools/dep_graph.py list --type cobol`.
- Review dependents of a component: `./tools/dep_graph.py dependents <NAME>`.

## Work Sequencing
- **Phase 1 – Core Transactions (serial):** Continue through customer and policy front-end programs (`LGAPOL01`, `LGAPVS01`, `LGACUS01`, etc.), pairing each with its backing DB module so request/response flows stay consistent.
- **Phase 2 – Data Services (serial):** Document batch/database utilities (`LGAPDB01`, `LGDPDB01`, `LGIPDB01`, `LGUCDB01`) and shared logging (`LGSTSQ`) once their callers are understood.
- **Phase 3 – Shared Assets (parallel):** Tackle copybooks and BMS maps alongside transaction work; these can be owned by separate teammates with ongoing updates.
  - **Phase 3 Task 1:** Document core copybooks (`LGCMAREA`, `LGPOLICY`) - shared data structures
  - **Phase 3 Task 2:** Document lookup copybooks (`POLLOOK`, `POLLOO2`) - reference data structures  
  - **Phase 3 Task 3:** Document SOA interface copybooks (`SOAIC01`, `SOAIPB1`, `SOAIPE1`, `SOAIPH1`, `SOAIPM1`) - service interfaces
  - **Phase 3 Task 4:** Document SOA data copybooks (`SOAVCII`, `SOAVCIO`, `SOAVPII`, `SOAVPIO`) - service data exchange
  - **Phase 3 Task 5:** Document BMS maps (`SSMAP.bms`) - screen layouts and field definitions
- **Phase 4 – Ops & Automation (parallel):** While COBOL review continues, inventory operational artifacts and cross-link to program dependencies.
  - **Phase 4 Task 1:** Document CICS definition JCL (`ADEF121`, `CDEF121-125`) - transaction and program definitions
  - **Phase 4 Task 2:** Document compilation JCL (`COBOL`, `ASMMAP`, `DB2BIND`) - build and deployment jobs
  - **Phase 4 Task 3:** Document database setup JCL (`DB2CRE`, `DB2DEL`, `DEFDREP`, `DEFWREP`) - data management jobs
  - **Phase 4 Task 4:** Document workload simulation JCL (`ITPENTR`, `ITPLL`, `ITPSTL`, `SAMPCMA`, `SAMPNCS`, `SAMPTSQ`, `SAMPWUI`) - testing infrastructure
  - **Phase 4 Task 5:** Document web service JCL (`WSA*` series) - service automation jobs
  - **Phase 4 Task 6:** Document REXX automation (`CUST1.REXX`, `MAC1.REXX`) - operational scripts
  - **Phase 4 Task 7:** Document installation automation (`install.sh`) - deployment and setup processes
- **Phase 5 – Data & Simulation (parallel):** In parallel with ops review, analyze test data and simulation assets.
  - **Phase 5 Task 1:** Document sample datasets (`KSDSCUST.TXT`, `KSDSPOLY.TXT`) - customer and policy test data
  - **Phase 5 Task 2:** Document simulation configuration (`GENAPP.TXT`, `#SSVARS.TXT`) - workload simulator setup
  - **Phase 5 Task 3:** Document transaction simulation scripts (`SSC1*`, `SSP1*`, `SSP2*`, `SSP3*`, `SSP4*`) - individual transaction flows
  - **Phase 5 Task 4:** Document web service simulation (`WSC1*`, `WSLGCF`) - web interface test scenarios
  - **Phase 5 Task 5:** Document reference data files (`CCOLOR`, `CMAKE`, `CMODEL`, `CTYPE`, `FNAME`, `HTYPE`, `PCODE`, `PTYPE`, `RTYPE`, `SNAME`) - lookup tables and validation data
  - **Phase 5 Task 6:** Document error and control flows (`ONCICS`, `STOP`, `WASERROR`) - simulation control and exception handling
  - **Phase 5 Task 7:** Document event bindings (`Transaction_Counters.evbind`) - CICS monitoring configuration

## Parallelization Notes
- Pair front-end and back-end COBOL modules in the same lane to avoid re-reading shared commareas.
- Assign separate owners for shared copybooks/maps and for infrastructure artifacts (JCL/REXX/data) so updates proceed without blocking the core transaction walkthrough.
- Revisit the dependency graph after each phase to confirm cross-stream updates stay synchronized.
