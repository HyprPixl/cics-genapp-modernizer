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

### LGACDB02 – Customer Security Service
- Purpose: specialized customer security service that manages customer authentication credentials in the `CUSTOMER_SECURE` table.
- Interfaces: uses custom commarea structure with customer number, encrypted password, security state indicator, and password change count fields.
- Dependencies: DB2 `CUSTOMER_SECURE` table, `LGCMAREA` and `LGPOLICY` copybooks for data structures, `LGSTSQ` for error logging.
- Error Handling: validates request ID (`02ACUS` for new customer security add), returns `99` for unrecognized requests, `98` for SQL insertion failures.
- Notes: handles secure customer credentials separately from main customer profile; supports password state management and change tracking; integrates with main customer add workflow via `LGACDB01`.

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

### LGDPDB01 – Delete Policy Database Service
- Purpose: DB2-backed policy deletion service that removes policy records from the main POLICY table leveraging cascading foreign key relationships.
- Interfaces: requires `LGCMAREA` with customer and policy numbers for targeted deletion; validates specific request IDs (`01DEND`, `01DHOU`, `01DCOM`, `01DMOT`).
- Dependencies: DB2 `POLICY` table (primary), cascaded child tables via foreign keys, `LGDPVS01` (VSAM cleanup), `LGCMAREA` copybook, `LGSTSQ` for error logging.
- Error Handling: returns code `99` for unrecognized request IDs, `90` for SQL errors; logs detailed diagnostic information including customer/policy numbers and SQL codes.
- Notes: performs single DELETE against POLICY table relying on DB2 foreign key constraints to cascade deletion to child policy-type tables; invokes `LGDPVS01` for VSAM synchronization after successful DB2 operation.

### LGIPDB01 – Inquire Policy Database Service
- Purpose: comprehensive policy inquiry service supporting multiple query types (single policy, customer policies, geographic searches) with cursor-based result sets.
- Interfaces: accepts various request IDs (`01IEND`, `01IHOU`, `01IMOT`, `01ICOM`, `02ICOM`, `03ICOM`, `05ICOM`) with corresponding policy type-specific data structures in commarea.
- Dependencies: DB2 tables (`POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`, `COMMERCIAL`), `LGCMAREA` and `LGPOLICY` copybooks for data mapping, `LGSTSQ` for error logging.
- Error Handling: returns `01` for no records found, `90` for SQL errors, `98` for insufficient commarea length; comprehensive cursor management with cleanup on errors.
- Notes: uses DB2 cursors for multi-row commercial policy searches; handles nullable fields with indicator variables; dynamically calculates required commarea sizes based on variable-length policy data.

### LGICDB01 – Inquire Customer Database Service  
- Purpose: simple customer information retrieval service that queries the CUSTOMER table by customer number and returns complete customer profile.
- Interfaces: expects `LGCMAREA` with customer number; returns full customer details including personal information, address, and contact details.
- Dependencies: DB2 `CUSTOMER` table, `LGCMAREA` and `LGPOLICY` copybooks for field definitions, `LGSTSQ` for error logging.
- Error Handling: returns `01` for customer not found or deadlock conditions (`-913`), `90` for other SQL errors, `98` for insufficient commarea length.
- Notes: straightforward single-row SELECT operation; validates minimum commarea length to accommodate customer data structure; includes comprehensive error logging with SQL diagnostic information.

### LGUCDB01 – Update Customer Database Service
- Purpose: customer information update service that modifies customer profile data in DB2 and synchronizes changes to VSAM via `LGUCVS01`.
- Interfaces: consumes `LGCMAREA` with updated customer details including names, birth date, address, phone numbers, and email address.
- Dependencies: DB2 `CUSTOMER` table, `LGUCVS01` (VSAM synchronization), `LGCMAREA` and `LGPOLICY` copybooks, `LGSTSQ` for error logging.
- Error Handling: returns `01` for customer not found, `90` for SQL errors; logs detailed diagnostic information including customer number and SQL operation results.
- Notes: performs comprehensive customer profile update with nine field modifications; automatically invokes `LGUCVS01` to maintain VSAM file consistency after successful DB2 update.

### LGUPDB01 – Update Policy Database Service
- Purpose: sophisticated policy update service supporting endowment, house, and motor policy modifications with optimistic concurrency control via timestamp validation.
- Interfaces: handles request IDs (`01UEND`, `01UHOU`, `01UMOT`) with corresponding policy-specific data structures; includes broker and payment information updates.
- Dependencies: DB2 tables (`POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`), `LGUPVS01` (VSAM sync), `LGCMAREA` and `LGPOLICY` copybooks, `LGSTSQ` for error logging, DB2 cursors for row locking.
- Error Handling: returns `01` for policy not found, `02` for timestamp mismatch (concurrent update), `90` for SQL errors; includes transaction rollback on failures and comprehensive cursor cleanup.
- Notes: uses DB2 cursor with FOR UPDATE to lock policy records; validates last-changed timestamp to detect concurrent modifications; updates both main POLICY table and policy-type-specific tables; refreshes timestamp and synchronizes to VSAM on successful completion.

## Phase 4 – Operational Infrastructure & Automation

### CICS Definition JCL (Task 1)

#### ADEF121 – VSAM File Allocation & Population
- Purpose: comprehensive VSAM cluster setup for GenApp customer and policy data files with initial data loading.
- Components: defines `KSDSCUST` (customer, 225-byte records, 10-char key) and `KSDSPOLY` (policy, 64-byte records, 21-char key) KSDS clusters.
- Dependencies: requires `<USRHLQ>`, `<KSDSCUS>`, and `<KSDSPOL>` dataset references; uses SYSDAV volume allocation.
- Operations: DELETE/DEFINE cycle with conditional data loading via REPRO commands; includes FREESPACE(10,10) for growth management.
- Error Handling: tolerates MAXCC=8 on delete operations for initial setup scenarios; COND parameters prevent data load on definition failures.

#### CDEF121-125 – CICS Region Definition Series
- **CDEF121**: TOR (Terminal Oriented Region) configuration with TCPIP support, security disabled, multi-threading (MXT=600), and LE memory limits.
- **CDEF122**: AOR (Application Oriented Region) with DB2 connectivity, extensive error suppression (XDCT=NO, XFCT=NO), and high-volume transaction processing.
- **CDEF123**: DOR (Data Oriented Region) specialized for database operations with RLS support, named counter pools, and enhanced storage protection.
- **CDEF124**: CMAS (CICSPlex System Manager Administration Server) with minimal system resource requirements and focused applicability.
- **CDEF125**: WUI (Web User Interface) server for browser-based CICS administration with TCPIP ports 6345/6346 and CICSPlex connectivity.
- Shared Dependencies: all regions require `<CICSHLQ>`, `<CICSLIC>`, `<CPSMHLQ>`, `<CEEHLQ>`, and customized `<USRHLQ>` datasets.

### Compilation JCL (Task 2)

#### COBOL – Enterprise COBOL Compilation Procedure
- Purpose: standardized DB2-integrated COBOL compilation with CICS preprocessing for all GenApp transaction programs.
- Process Flow: COBOL compile → DFHEILIA reblock → linkage editor with comprehensive library resolution.
- Dependencies: Enterprise COBOL compiler (`<COBOLHLQ>`), CICS translator (`<CICSHLQ>`), DB2 precompiler (`<DB2HLQ>`), LE runtime (`<CEEHLQ>`).
- Compilation Options: NODYNAM, RENT, APOST, CICS enablement, CODEPAGE (`<DB2CCSID>`) for international character support.
- Target Programs: compiles all 22 GenApp modules including transaction frontends, database services, VSAM handlers, and test utilities.

#### ASMMAP – Assembler Map Compilation
- Purpose: BMS (Basic Mapping Support) map assembly for CICS screen definitions.
- Process: assembles `.bms` source into map copybooks and load modules for terminal-based transaction interfaces.
- Dependencies: CICS assembler libraries, MAPSET generation utilities, load module placement for runtime access.

#### DB2BIND – Database Access Path Optimization
- Purpose: creates optimized DB2 access paths for all GenApp programs with database connectivity.
- Components: binds DBRM (Database Request Module) packages for 18 DB2-enabled programs including customer/policy operations and test utilities.
- Configuration: isolation level CS (Cursor Stability), dynamic SQL rules, CURRENTDATA(NO) for read efficiency, batch and CICS enablement.
- Dependencies: DB2 system (`<DB2SSID>`), collection (`GENASA1`), and `<DBRMLIX>` library for compiled database request modules.

### Database Setup JCL (Task 3)

#### DB2CRE – Complete Database Schema Creation
- Purpose: comprehensive GenApp database environment setup including storage groups, databases, tablespaces, tables, indexes, security, and sample data.
- Schema Components:
  - **Storage**: GENASG02 storage group with VCAT integration and 7 specialized tablespaces (GENATS01-07) with buffer pool optimization.
  - **Tables**: CUSTOMER (identity-based), CUSTOMER_SECURE (credential vault), POLICY (master), plus type-specific tables (ENDOWMENT, HOUSE, MOTOR, COMMERCIAL, CLAIM).
  - **Relationships**: comprehensive foreign key constraints with cascade delete for referential integrity.
  - **Indexes**: clustered primary indexes plus secondary access paths for customer-to-policy relationships.
- Sample Data: 10 customers, 10 policies across all types, 2 endowments, 3 houses, 3 motor vehicles, 2 commercial properties.
- Security: grants all privileges to PUBLIC for development/test environment access.

#### DB2DEL – Database Cleanup Utility
- Purpose: removes GenApp database objects in proper dependency order for environment refresh or decommissioning.
- Process: drops tables, tablespaces, database, and storage group with CASCADE options for complete cleanup.
- Safety: designed for development environments; requires manual verification before production use.

#### DEFDREP/DEFWREP – CPSM Repository Management
- Purpose: CICSPlex System Manager (CPSM) repository definition and workload management setup.
- DEFDREP: creates CPSM data repository with appropriate sharing and recovery characteristics.
- DEFWREP: establishes workload repository for transaction distribution and load balancing across CICS regions.

### Workload Simulation JCL (Task 4)

#### ITPENTR – Interactive Test Environment Setup
- Purpose: establishes terminal emulation environment for GenApp transaction testing.
- Components: CICS region startup with terminal definitions and user session management.
- Dependencies: CICS system datasets, terminal control definitions, user security profiles.

#### ITPLL/ITPSTL – Load Testing Infrastructure
- Purpose: high-volume transaction load generation and stress testing capabilities.
- ITPLL: lightweight load driver for sustained transaction volume testing.
- ITPSTL: sophisticated test scenarios with transaction mix control and performance measurement.

#### SAMPCMA/SAMPWUI/SAMPNCS/SAMPTSQ – Service Component Testing
- **SAMPCMA**: CICS Management Agent testing for CICSPlex operations and monitoring.
- **SAMPWUI**: Web User Interface component validation with browser-based admin interface testing.
- **SAMPNCS**: Named Counter Server testing for customer/policy number generation validation.
- **SAMPTSQ**: Temporary Storage Queue testing for LGSTSQ logging infrastructure validation.

### Web Service JCL (Task 5 - WSA* Series)

#### Policy Management Web Services
- **WSAAP01**: Motor, House, Endowment, and Commercial policy ADD operations via SOAP web services using DFHLS2WS converter.
- **WSAIP01**: comprehensive policy INQUIRY web services with type-specific request/response structures.
- **WSAUP01**: policy UPDATE operations with optimistic concurrency control via web service interfaces.

#### Customer Management Web Services  
- **WSAAC01**: customer ADD operations with web service integration for customer onboarding.
- **WSAIC01**: customer INQUIRY services for customer profile retrieval via web interfaces.
- **WSAUC01**: customer UPDATE operations maintaining VSAM synchronization through web service calls.

#### Web Service Architecture
- **WSAVC01/WSAVP01**: VSAM integration web services for customer and policy data synchronization.
- Technology Stack: IBM CICS Web Services, DFHLS2WS language structure converter, SOAP protocol support.
- Dependencies: z/OS USS environment (`<ZFSHOME>`), Java runtime, CICS Web Services infrastructure, proxy configuration.

### REXX Automation (Task 6)

#### CUST1.REXX – GenApp Customization Engine
- Purpose: comprehensive environment-specific customization of all GenApp JCL, scripts, and configuration files.
- Functionality: 
  - Variable substitution across 29 configurable parameters (CICS, DB2, COBOL HLQs, system IDs, dataset names).
  - Automated library allocation for DBRMLIB, MAPCOPY, LOAD, and MSGTXT datasets.
  - Batch processing of all members in GENAPP.CNTL dataset with MAC1.REXX macro execution.
  - ISPF dialog integration with variable pool management for interactive customization.
- Target Scope: processes all JCL members plus WSIM simulation configuration for complete environment setup.
- Dependencies: ISPF services, TSO ALTLIB for REXX library management, MAC1.REXX macro processor.

#### MAC1.REXX – Template Processing Macro
- Purpose: ISPF edit macro for systematic parameter substitution across GenApp configuration files.
- Processing: performs global string replacement for 26+ environment-specific variables (CICS regions, DB2 systems, dataset qualifiers).
- Integration: called by CUST1.REXX for each member requiring customization; handles both JCL and simulation script templates.
- Special Handling: renames processed members with @ prefix for deployment readiness, handles ONCICS simulation file specially.

### Installation Automation (Task 7)

#### install.sh – USS Deployment Script
- Purpose: automated deployment of GenApp components from USS filesystem to z/OS datasets for CICS/DB2 environment setup.
- Deployment Process:
  1. **JCL Setup**: allocates and populates `${GENAPP}.CNTL` with all control scripts and procedures.
  2. **REXX Setup**: deploys customization and automation scripts to `${GENAPP}.EXEC`.
  3. **Source Setup**: copies COBOL programs, copybooks, BMS maps, and text files to `${GENAPP}.SRC`.
  4. **Simulation Setup**: installs workload simulation scripts to `${GENAPP}.WSIM`.
  5. **Data Setup**: creates and loads sample customer/policy datasets with appropriate record formats.
- Dataset Configuration: automatically determines optimal allocation parameters (LRECL, BLKSIZE, SPACE) for each component type.
- Dependencies: USS environment with `tsocmd` utility, appropriate TSO/ISPF authority for dataset allocation, connectivity to target z/OS system.

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
