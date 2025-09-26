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
- Purpose: front-end CICS task for creating a new customer record; validates commarea structure before delegating persistence to `LGACDB01`.
- Interfaces: expects `DFHCOMMAREA` shaped by `LGCMAREA` with customer data payload; initializes `CA-RETURN-CODE` to `00` and `CA-NUM-POLICIES` to `00` on entry.
- Dependencies: `LGACDB01` (database insert), `LGSTSQ` (TDQ error logging), `LGCMAREA` copybook for shared structures, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with code `LGCA` when no commarea provided; returns code `98` for insufficient commarea length; writes timestamped diagnostic entries via `LGSTSQ`.
- Follow-ups: document `LGACDB01` data-handling logic and confirm expected commarea layout for customer adds.

### LGACDB01 – Customer Database Writer
- Purpose: DB2-backed customer add service that inserts customer records and invokes VSAM replication and security services.
- Interfaces: requires `LGCMAREA` with customer details; uses `LGPOLICY` copybook for field definitions and DB2 host variables.
- Dependencies: DB2 `CUSTOMER` table, `LGACVS01` (VSAM sync), `LGACDB02` (customer security), named counter `GENACUSTNUM` from pool `GENA`, `LGSTSQ` for logging, `LGCMAREA` copybook.
- Error Handling: handles counter unavailability by using DB2 `DEFAULT` for customer number assignment; translates SQLCODEs to return code `90`; logs SQL requests and results.
- Notes: attempts to obtain customer number from CICS named counter first, falls back to DB2 identity generation; updates commarea with assigned customer number.

### LGACVS01 – Customer VSAM Writer
- Purpose: writes customer summary records into VSAM KSDS `KSDSCUST` after `LGACDB01` processes DB2 customer insertion.
- Interfaces: consumes `LGCMAREA` customer data starting from `CA-Customer-Num`; expects 225-byte customer record format.
- Dependencies: VSAM file `KSDSCUST`, `LGSTSQ` for TDQ logging, `LGCMAREA` copybook, CICS file control APIs.
- Error Handling: non-normal file `RESP` results set `CA-RETURN-CODE` to `80`, log failure details via `LGSTSQ`, and abend with `LGV0` to preserve transaction integrity.
- Notes: uses customer number as both record key and starting field; ensures diagnostic data includes RESP/RESP2 codes for file operation troubleshooting.

### LGICUS01 – Inquire Customer Transaction
- Purpose: front-end CICS task for retrieving customer information; validates commarea structure before delegating lookup to `LGICDB01`.
- Interfaces: expects `DFHCOMMAREA` shaped by `LGCMAREA` with customer inquiry payload; initializes `CA-RETURN-CODE` to `00` and `CA-NUM-POLICIES` to `00` on entry.
- Dependencies: `LGICDB01` (database query), `LGSTSQ` (TDQ error logging), `LGCMAREA` copybook, `LGPOLICY` for field definitions, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with code `LGCA` when no commarea provided; returns code `98` for insufficient commarea length; writes timestamped diagnostic entries via `LGSTSQ`.
- Notes: requires commarea length to accommodate both header/trailer (18 bytes) plus customer data structure from `LGPOLICY` copybook.

### LGUCUS01 – Update Customer Transaction  
- Purpose: front-end CICS task for updating customer details; validates request ID and delegates modification to `LGUCDB01`.
- Interfaces: expects `DFHCOMMAREA` shaped by `LGCMAREA` with request ID `01UCUS` and customer update payload; initializes return codes on entry.
- Dependencies: `LGUCDB01` (database update), `LGSTSQ` (TDQ error logging), `LGCMAREA` copybook for shared structures, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with code `LGCA` when no commarea provided; returns code `99` for unrecognized request ID; writes timestamped diagnostic entries via `LGSTSQ`.
- Notes: includes VARCHAR field handling capability with 3900-character variable data support; validates specific request ID before processing.

### LGIPOL01 – Inquire Policy Transaction
- Purpose: front-end CICS task for retrieving policy information; delegates lookup to `LGIPDB01` backend service.
- Interfaces: expects `DFHCOMMAREA` shaped by `LGCMAREA` with policy inquiry payload; initializes `CA-RETURN-CODE` to `00` on entry.
- Dependencies: `LGIPDB01` (database query), `LGSTSQ` (TDQ error logging), `LGCMAREA` copybook, `LGPOLICY` for field definitions, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with code `LGCA` when no commarea provided; writes timestamped diagnostic entries via `LGSTSQ` and preserves commarea contents for debugging.
- Notes: simple front-end that performs minimal validation before delegating all inquiry logic to database backend service.

### LGUPOL01 – Update Policy Transaction
- Purpose: front-end CICS task for updating policy details; validates request type and commarea length before delegating to `LGUPDB01`.
- Interfaces: expects `DFHCOMMAREA` shaped by `LGCMAREA` with update request IDs (`01UEND`, `01UHOU`, `01UMOT`) and corresponding policy data.
- Dependencies: `LGUPDB01` (database update), `LGSTSQ` (TDQ error logging), `LGCMAREA` copybook, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with code `LGCA` when no commarea provided; returns code `98` for insufficient length, `99` for unrecognized request ID; comprehensive error logging.
- Notes: calculates required commarea length based on policy type (Endowment: 124, House: 130, Motor: 137 bytes) plus 28-byte header.

### LGDPOL01 – Delete Policy Transaction
- Purpose: front-end CICS task for deleting policy records; validates request type before delegating deletion to `LGDPDB01`.
- Interfaces: expects `DFHCOMMAREA` shaped by `LGCMAREA` with delete request IDs (`01DEND`, `01DMOT`, `01DHOU`, `01DCOM`) and policy identifier.
- Dependencies: `LGDPDB01` (database deletion), `LGSTSQ` (TDQ error logging), `LGCMAREA` copybook, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with code `LGCA` when no commarea provided; returns code `98` for insufficient length, `99` for unrecognized request ID; early return on deletion errors.
- Notes: converts request ID to uppercase for validation; supports all four policy types (Endowment, Motor, House, Commercial) for deletion operations.

### LGSTSQ – Shared Logging Service
- Purpose: centralized diagnostic logging service that writes messages to both transient data queues (TDQ) and temporary storage queues (TSQ) for GenApp error tracking.
- Interfaces: can be invoked via CICS `LINK` with 90-byte commarea containing diagnostic message, or called as transaction via `RECEIVE` from terminal input.
- Dependencies: CICS transient data queue `CSMT`, temporary storage queue `GENAnnnn` (where `nnnn` comes from optional `Q=nnnn` parameter), CICS commands (`ASSIGN`, `WRITEQ TD`, `WRITEQ TS`, `RECEIVE`, `SEND`, `RETURN`).
- Error Handling: uses `NOSUSPEND` option for TSQ writes to avoid task suspension when queue space unavailable; continues operation regardless of individual queue write failures.
- Notes: detects invocation method via `ASSIGN INVOKINGPROG` - called programs get commarea route, terminal transactions get `RECEIVE` route; supports custom queue naming via `Q=nnnn` prefix in message content.

### LGDPDB01 – Delete Policy Database Writer
- Purpose: DB2-backed policy deletion service that removes policy records from the POLICY table and coordinates VSAM cleanup via `LGDPVS01`.
- Interfaces: requires `LGCMAREA` with customer number, policy number, and request ID; supports deletion request IDs (`01DEND`, `01DHOU`, `01DCOM`, `01DMOT`).
- Dependencies: DB2 `POLICY` table, `LGDPVS01` (VSAM deletion), `LGCMAREA` copybook, `LGSTSQ` for error logging, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with `LGCA` when no commarea provided; returns code `98` for insufficient length, `99` for unrecognized request ID, `90` for SQL failures; logs comprehensive error details including customer/policy numbers and SQL operations.
- Notes: relies on DB2 foreign key constraints for proper deletion order; treats both SQLCODE 0 and 100 (not found) as successful; always attempts VSAM cleanup via `LGDPVS01` after successful DB2 deletion.

### LGIPDB01 – Inquire Policy Database Reader
- Purpose: comprehensive DB2-backed policy inquiry service supporting multiple policy types with complex join queries and cursor-based data retrieval.
- Interfaces: requires `LGCMAREA` with customer number, policy number, and request ID; supports inquiry request IDs (`01IEND`, `01IHOU`, `01IMOT`, `01ICOM`, `02ICOM`, `03ICOM`, `05ICOM`).
- Dependencies: DB2 tables (`POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`, `COMMERCIAL`), `LGCMAREA` copybook, `LGPOLICY` SQL include, `LGSTSQ` for error logging, CICS commands (`RETURN`, `ASKTIME`).
- Error Handling: abends with `LGCA` when no commarea provided; returns code `99` for unrecognized request ID, `88` for cursor operation failures; comprehensive error logging with SQL operation details and customer/policy context.
- Notes: handles variable-length data fields with indicator variables; uses scroll cursors for commercial policy zip code-based queries; calculates dynamic commarea lengths based on retrieved data size including padding fields.

### LGUCDB01 – Update Customer Database Writer
- Purpose: DB2-backed customer update service that modifies customer records in the CUSTOMER table and coordinates VSAM synchronization via `LGUCVS01`.
- Interfaces: requires `LGCMAREA` with customer number and updated customer fields (name, address, phone, email); uses fixed 225-byte commarea for VSAM sync.
- Dependencies: DB2 `CUSTOMER` table, `LGUCVS01` (VSAM sync), `LGCMAREA` copybook, `LGPOLICY` for field definitions, `LGSTSQ` for error logging, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with `LGCA` when no commarea provided; returns code `01` for customer not found (SQLCODE 100), `90` for other SQL failures; comprehensive error logging with customer context and SQL operation details.
- Notes: updates comprehensive customer profile including personal details, address, and contact information; always invokes VSAM synchronization after successful DB2 update to maintain data consistency across storage systems.

### LGICDB01 – Inquire Customer Database Reader
- Purpose: DB2-backed customer inquiry service that retrieves complete customer details from the CUSTOMER table using single-row SELECT operations.
- Interfaces: requires `LGCMAREA` with customer number; returns customer profile data including personal details, address, and contact information directly in commarea.
- Dependencies: DB2 `CUSTOMER` table, `LGCMAREA` copybook, `LGPOLICY` for field definitions, `LGSTSQ` for error logging, CICS commands (`RETURN`, `ASKTIME`).
- Error Handling: abends with `LGCA` when no commarea provided; returns code `98` for insufficient commarea length, `01` for customer not found (SQLCODE 100) or deadlock (SQLCODE -913), `90` for other SQL failures; detailed error logging with customer context.
- Notes: performs comprehensive commarea length validation based on customer record size; populates all customer fields directly into commarea structure for efficient data transfer to caller.

### LGUPDB01 – Update Policy Database Writer
- Purpose: DB2-backed policy update service that modifies policy records across multiple policy tables (Endowment, House, Motor) and coordinates VSAM synchronization via `LGUPVS01`.
- Interfaces: requires `LGCMAREA` with customer number, policy number, and request ID; supports update request IDs (`01UEND`, `01UHOU`, `01UMOT`) with corresponding policy data.
- Dependencies: DB2 tables (`POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`), `LGUPVS01` (VSAM sync), `LGCMAREA` copybook, `LGPOLICY` for field definitions, `LGSTSQ` for error logging, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with `LGCA` when no commarea provided; returns code `90` for SQL failures including deadlocks (SQLCODE -913); uses cursor-based locking for timestamp validation and optimistic concurrency control.
- Notes: uses POLICY_CURSOR for record locking and timestamp validation; performs type-specific updates based on request ID; always invokes VSAM synchronization after successful DB2 updates to maintain cross-system consistency.

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
