# CICS GenApp Modernizer

## Overview
- Modernization workspace for the IBM CICS GenApp sample application and supporting assets.
- Contains legacy COBOL programs, JCL procedures, REXX utilities, and data used to simulate the insurance workload.
- Goal: inventory and document the moving parts before proposing upgrades or refactors.

## Repository Layout
- `base/src/` legacy sources: COBOL programs (`lg*.cbl`), copybooks (`*.cpy`), BMS maps (`ssmap.bms`), and supporting text assets.
- `base/cntl/` JCL members for compiling programs, allocating datasets, and driving GenApp jobs.
- `base/exec/` REXX execs invoked during build or operations (`cust1.rexx`, `mac1.rexx`).
- Customer Experience Assets: `base/wsim/` workstation simulator flows, `base/event-bindings/` CICS event bindings, and `base/images/` reference diagrams.
- `base/bin/` utilities, notably `install.sh`, to allocate host datasets and upload members via `tsocmd` and USS `cp`.
- `base/data/` sample input datasets (`ksdscust.txt`, `ksdspoly.txt`) referenced by the application.

## Documentation Work Breakdown
- Legacy Programs: walk each `lg*.cbl` module, record purpose, entry points, and copybook usage.
- Shared Copybooks & Maps: describe `*.cpy` data structures and `ssmap.bms` screen definitions.
- Operations JCL: map every member in `base/cntl/` to its function (compile, bind, housekeeping, etc.).
- Automation & Tooling: review REXX execs and `install.sh` for deployment or setup automation.
- Data & Simulation Assets: capture how `data/` and `wsim/` files drive scenarios or tests.
- Platform Integrations: document `event-bindings/` artifacts and any external dependencies.

## Legacy Program Notes
### LGAPOL01 – Add Policy Transaction
- Purpose: front-end CICS task for creating a new insurance policy; validates commarea length before delegating persistence to `LGAPDB01`.
- Interfaces: expects `DFHCOMMAREA` shaped by `LGCMAREA` (minimum 28-byte header plus request payload) and initializes `CA-RETURN-CODE` to `00` on entry.
- Dependencies: `LGAPDB01` (database insert), `LGSTSQ` (TDQ error logging), `LGCMAREA` copybook for shared structures, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with code `LGCA` when no commarea provided; writes timestamped diagnostic entries via `LGSTSQ` and echoes failing commarea payload.
- Follow-ups: document `LGAPDB01` data-handling logic and confirm expected commarea layout for policy adds.

### LGAPVS01 – Policy VSAM Persistence Helper
- Purpose: writes policy summary records into VSAM KSDS `KSDSPOLY` after `LGAPDB01` allocates a policy number.
- Interfaces: consumes `LGCMAREA` to drive record keys/segments; expects `CA-REQUEST-ID` to provide policy type discriminator (`C`, `E`, `H`, `M`).
- Dependencies: VSAM file `KSDSPOLY`, `LGSTSQ` for TDQ logging, `LGCMAREA` copybook, CICS file control APIs.
- Error Handling: non-normal `RESP` results set `CA-RETURN-CODE` to `80`, log failure via `LGSTSQ`, and return without abend to allow caller control.
- Notes: ensures commarea snapshots go to TDQ on failure, preserving the request data used to build the record image.

### LGAPDB01 – Policy Database Writer
- Purpose: core add-policy back-end that inserts rows across DB2 tables before invoking `LGAPVS01` for VSAM replication.
- Interfaces: requires `LGCMAREA` payloads matching add-policy templates (`01AEND`, `01AHOU`, `01AMOT`, `01ACOM`); includes SQL copybook `LGPOLICY` for host variable definitions.
- Dependencies: DB2 tables (`POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`, `COMMERCIAL`), `LGAPVS01` (post-insert VSAM sync), `LGSTSQ` for logging, `LGCMAREA`, `LGPOLICY` SQL include, CICS DB2 commands (`EXEC SQL`), and TDQ infrastructure.
- Error Handling: translates SQLCODEs into GenApp return codes (`70`, `90`), logs details through `LGSTSQ`, and abends with `LGSQ` on downstream table failures to trigger unit-of-work backout.
- Notes: fetches generated policy number via `IDENTITY_VAL_LOCAL()` and updates commarea so caller can return the new identifier.

### LGACUS01 – Add Customer Transaction
- Purpose: validates incoming customer details and links to `LGACDB01` to persist the record, pre-filling counters such as `CA-NUM-POLICIES`.
- Interfaces: expects `LGCMAREA` header plus `LGPOLICY` customer payload; minimum commarea length is header (18) + customer section.
- Dependencies: `LGACDB01` (DB2 insert), `LGSTSQ` (logging), `LGCMAREA`/`LGPOLICY` copybooks, CICS counter services (via downstream `LGACDB01`).
- Error Handling: abends with `LGCA` if no commarea; sets `CA-RETURN-CODE` to `98` when payload too small and returns gracefully.

### LGACDB01 – Customer Database Writer
- Purpose: creates customer rows in DB2, optionally using a CICS counter to supply the key, and fan-outs to VSAM (`LGACVS01`) plus customer security (`LGACDB02`).
- Interfaces: uses `IDENTITY_VAL_LOCAL()` when counter unavailable; updates commarea with generated customer number for caller continuity.
- Dependencies: DB2 `CUSTOMER` table, CICS counter `GENACUSTNUM`, VSAM writer `LGACVS01`, security service `LGACDB02`, logging program `LGSTSQ`, copybooks `LGCMAREA`/`LGPOLICY`.
- Error Handling: maps SQL failures to `CA-RETURN-CODE` `90`, logs via `LGSTSQ`, and returns control without abend for caller retry; VSAM/linked program failures propagate via linked modules.

### LGACVS01 – Customer VSAM Persistence
- Purpose: writes the 225-byte customer snapshot to KSDS `KSDSCUST` keyed by customer number after DB2 insert succeeds.
- Interfaces: uses `LGCMAREA` to build record, `CICS WRITE FILE` to persist.
- Dependencies: VSAM `KSDSCUST`, `LGSTSQ` for diagnostics, `LGCMAREA` structure.
- Error Handling: sets `CA-RETURN-CODE` to `80` on VSAM errors, logs payload via `LGSTSQ`, and abends with `LGV0` to force DB2 rollback.

### LGICUS01 – Inquire Customer Transaction
- Purpose: front-end that retrieves customer profile data into the commarea for downstream experience channels.
- Interfaces: validates commarea sizing (header/trailer + customer block) before delegating to `LGICDB01`.
- Dependencies: `LGICDB01`, `LGCMAREA`/`LGPOLICY`, `LGSTSQ` for error capture.
- Error Handling: abends on missing commarea, sets `CA-RETURN-CODE` to `98` when request insufficient, leaving DB2 untouched.

### LGICDB01 – Customer DB2 Reader
- Purpose: reads `CUSTOMER` table details into commarea fields, translating SQL status codes into GenApp response codes.
- Interfaces: expects numeric customer number, using integer host variables; sets `CA-RETURN-CODE` to `00` for success, `01` for not found/lock, `90` for unexpected errors.
- Dependencies: DB2 `CUSTOMER`, `LGCMAREA`/`LGPOLICY`, `LGSTSQ` for diagnostics.
- Error Handling: logs SQLCODE on failure and returns without abend to allow caller to decide follow-on action.

### LGIPOL01 – Inquire Policy Transaction
- Purpose: driver that validates commarea presence before linking to DB2 reader `LGIPDB01` for policy-specific data.
- Interfaces: uses `LGCMAREA` for shared fields; simply links and returns on completion.
- Dependencies: `LGIPDB01`, `LGCMAREA`, CICS linking primitives, `LGSTSQ` on error paths.
- Error Handling: abends with `LGCA` if no commarea, otherwise defers to back-end for SQL error mapping.

### LGIPDB01 – Policy DB2 Reader
- Purpose: retrieves policy and related extension data (endowment, house, motor, commercial) plus supports commercial policy search cursors.
- Interfaces: requires uppercase `CA-REQUEST-ID` selectors (`01IEND`, `01IHOU`, etc.), uses `LGPOLICY` for host variables, and can populate multiple record layouts.
- Dependencies: DB2 tables (`POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`, `COMMERCIAL`), potential TS queues for commercial lookups, `LGCMAREA`, `LGSTSQ`.
- Error Handling: sets `CA-RETURN-CODE` based on SQLCODE (e.g., `00` success, `01` no data, `90` unexpected), logging through `LGSTSQ` and returning to caller for flow control.

### LGACDB02 – Customer Security Seeder
- Purpose: inserts default credentials for newly created customers into `CUSTOMER_SECURE`, using data passed from `LGACDB01`.
- Interfaces: accepts a compact commarea with request id `02ACUS`, hashed password, and retry counters.
- Dependencies: DB2 `CUSTOMER_SECURE`, `LGSTSQ` for logging, invoked as a linked routine.
- Error Handling: sets return code `98` on SQL failure while logging the commarea snapshot for investigation.

### LGUCDB01 – Customer Update Service
- Purpose: updates personal details in both DB2 and VSAM mirrors, maintaining data parity after profile edits.
- Interfaces: consumes `LGCMAREA` with populated customer fields and calls `LGUCVS01` to rewrite `KSDSCUST` once DB2 update succeeds.
- Dependencies: DB2 `CUSTOMER`, VSAM writer `LGUCVS01`, `LGSTSQ`, `LGCMAREA`/`LGPOLICY` copybooks.
- Error Handling: returns `01` for not-found, `90` for other SQL issues, logging via `LGSTSQ`; VSAM failures trigger abends in `LGUCVS01` to ensure rollback.

### LGUCVS01 – Customer VSAM Rewrite
- Purpose: re-reads and rewrites the `KSDSCUST` record to reflect updated customer data.
- Interfaces: uses `CICS READ/REWRITE FILE` operations with update locks.
- Dependencies: VSAM `KSDSCUST`, `LGSTSQ`, `LGCMAREA`.
- Error Handling: distinguishes read vs rewrite failures with return codes `81`/`82` and abends (`LGV1`/`LGV2`) to back out DB2 work.

### LGUPDB01 – Policy Update Service
- Purpose: coordinates updates to policy headers and extension tables, verifying optimistic concurrency with `LASTCHANGED` timestamp checks.
- Interfaces: requires fully populated `LGCMAREA` policy structures, uses cursor-based fetch/update and calls `LGUPVS01` to sync VSAM copies.
- Dependencies: DB2 tables (`POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`), VSAM updater `LGUPVS01`, `LGSTSQ`, `LGCMAREA`/`LGPOLICY`.
- Error Handling: logs concurrency conflicts (timestamp mismatch) and unexpected SQL issues via `LGSTSQ`; sets return codes to drive caller messaging.

### LGUPVS01 – Policy VSAM Rewrite
- Purpose: rehydrates VSAM record for policies after DB2 updates, mirroring logic used during adds.
- Interfaces: interprets `CA-REQUEST-ID` to fill policy-type-specific segments before rewriting `KSDSPOLY`.
- Dependencies: VSAM `KSDSPOLY`, `LGSTSQ`, `LGCMAREA`.
- Error Handling: sets return codes `81`/`82` for read/write issues and abends (`LGV3`/`LGV4`) so DB2 changes roll back.

### LGSTSQ – Logging Utility
- Purpose: central telemetry routine that writes diagnostic records to TDQ `CSMT` and TSQ `GENAxxxx`, optionally routing by queue suffix (`Q=nnnn`).
- Interfaces: can be driven interactively or via `LINK`, accepting 90-byte payloads from callers.
- Dependencies: CICS TDQ/TSQ infrastructure; acts as shared sink for all transactional modules.
- Error Handling: relies on CICS response codes; no explicit abend behavior, but ensures request payloads survive for post-mortem review.
## Shared Copybooks & Maps
### LGCMAREA
- Purpose: canonical commarea layout shared by all transactions; defines request header, customer block, and polymorphic policy segments.
- Notes: includes multiple REDEFINES layers for policy sub-types (endowment, house, motor, commercial, claims) enabling reuse across flows.

### LGPOLICY
- Purpose: embedded SQL host variable definitions aligning COBOL structures with DB2 columns used in policy/customer modules.
- Notes: supplies length constants (e.g., `WS-CUSTOMER-LEN`) and integer host variables referenced during commarea validation.

### POLLOOK / POLLOO2
- Purpose: lightweight request copybooks for list and lookup operations (`POLLOOK` minimal header, `POLLOO2` five-policy array template).
- Notes: useful for service wrappers that do not require full `LGCMAREA`.

### SSMAP.BMS
- Purpose: BMS mapset supplying 3270 presentation for GenApp workflows (customer/policy panels, message lines).
- Notes: map fields mirror commarea segments, easing screen-to-transaction mapping.

## Ops & Automation Assets
### CNTL JCL Library
- `cobol.jcl` defines a reusable PROC for COBOL/DB2 compile-link steps; other `cdef12*.jcl` and `wsa*.jcl` members customize region setup, sample workloads, and CPSM definitions.
- Jobs such as `db2cre.jcl`/`db2del.jcl` provision or tear down DB2 artifacts, while `itp*.jcl` drive integration test pipelines.

### EXEC REXX Utilities
- `cust1.rexx` seeds ISPF variables, allocates GenApp datasets, and drives member customization macros.
- `mac1.rexx` provides the replace logic invoked by `cust1.rexx`, ensuring tailored members land in the correct PDS targets.

### bin/install.sh
- Shell wrapper that allocates z/OS data sets via `tsocmd` and uploads members from USS using `cp -O` dataset mode.
- Requires dataset support in the USS environment and correct `${USER}.GENAPP` high-level qualifier.

## Data & Simulation Assets
### base/data
- `ksdscust.txt` and `ksdspoly.txt` provide flat-file extracts used to prime the KSDS VSAM clusters; `install.sh` copies them with record formats matching the live datasets.

### base/wsim
- Workstation Simulator scripts (`ssc*`, `ssp*`, `wsc*`, etc.) model typical customer journeys (add, inquiry, update, delete) and rely on shared variables in `#ssvars.txt`.
- Scripts drive randomized test data via utility tables (`utbl`) and integrate with monitoring hooks (EMAIL, STOP labels) for automated runs.

### base/event-bindings
- `Transaction_Counters.evbind` captures LINK API invocations for programs beginning with `LG`, emitting request type and return code metrics via CICS event processing.

## Immediate Findings & Questions
- `install.sh` expects `tsocmd` and USS `cp` with dataset support; confirm environment prerequisites.
- Customer experience assets hint at established monitoring and test flows; identify current owners.
- Need to verify whether source members align with current CICS region configuration.
- Images folder currently holds `initial_topology.jpg`; consider exporting architecture notes from there.

## Next Steps
- Inventory high-priority COBOL transactions first (e.g., customer inquiry vs policy update paths).
- Decide documentation template for program deep-dives; store drafts alongside `AGENTS.md` notes.
- Align with operations to validate JCL sequencing before running in target environment.
- Capture modernization goals (e.g., API enablement, refactoring) once stakeholder input arrives.
