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

## Phase 5 – Data & Simulation Assets

### Sample Test Data Documentation

#### KSDSCUST.TXT – Customer Test Dataset
- **Purpose**: Sample customer records for testing VSAM KSDS operations via programs like `LGACVS01`, `LGUCVS01`, and `LGICVS01`.
- **Format**: Fixed-length records, 225 bytes per record (consistent with `CUSTOMER-RECORD-SIZE` in COBOL).
- **Record Count**: 10 test customer records (customers 0000000001 through 0000000010, complete sequence; file missing final newline).
- **Key Structure**: 10-byte customer number (positions 1-10), zero-padded.
- **Field Layout** (based on `LGCMAREA` copybook structure):
  - Customer Number: positions 1-10 (PIC 9(10))
  - First Name: positions 11-20 (PIC X(10))
  - Last Name: positions 21-40 (PIC X(20))
  - Date of Birth: positions 41-50 (PIC X(10), format YYYY-MM-DD)
  - House Name: positions 51-70 (PIC X(20))
  - House Number: positions 71-74 (PIC X(4))
  - Postcode: positions 75-82 (PIC X(8))
  - Number of Policies: positions 83-85 (PIC 9(3))
  - Mobile Phone: positions 86-105 (PIC X(20))
  - Home Phone: positions 106-125 (PIC X(20))
  - Email Address: positions 126-225 (PIC X(100))
- **Dependencies**: Corresponds to `CA-CUSTOMER-REQUEST` structure in `LGCMAREA` copybook; used by customer VSAM programs.
- **Test Coverage**: Includes varied customer profiles (ages from 1934-1969 births), diverse address formats (postcodes like "PI101O", "TB14TV"), mixed phone number combinations, and email addresses from different domains.

#### KSDSPOLY.TXT – Policy Test Dataset
- **Purpose**: Sample policy records for testing VSAM KSDS operations via programs like `LGAPVS01`, `LGUPVS01`, `LGDPVS01`, and `LGIPVS01`.
- **Format**: Fixed-length records, 64 bytes per record (consistent with policy VSAM file definitions).
- **Record Count**: 10 test policy records covering all four policy types.
- **Key Structure**: 21-byte composite key (positions 1-21):
  - Policy Type ID: position 1 (C/E/H/M for Commercial/Endowment/House/Motor)
  - Customer Number: positions 2-11 (PIC 9(10), zero-padded)
  - Policy Number: positions 12-21 (PIC 9(10), zero-padded)
- **Policy Type Distribution**:
  - **Commercial** (C): 2 policies (customers 1, 5)
  - **Endowment** (E): 2 policies (customers 3, 8)
  - **House** (H): 3 policies (customers 4, 6, 9)
  - **Motor** (M): 3 policies (customers 2, 5, 10)
- **Field Layout Examples** (positions 22-64, type-specific):
  - **Commercial** (C): Examples include "IBM" and "Clarets Merchandise" business names with postcodes and status indicators
  - **Endowment** (E): Life assured names like "Shep" and "J. MORRIS" with fund management flags (Y/N indicators for profits, equities)
  - **House** (H): Property types (HOUSE/FARM/FLAT), bedroom counts (5/0/1), values (£150K-£375K), postcodes (SO211UP, SO529ED, E15WW)
  - **Motor** (M): Vehicle makes (FORD/DENNIS/VOLKSWAGEN), models (KA/ENGINE/BEETLE), values (£600-£85K), registrations (LL60LOO, FIRE1, A567WWR)
- **Dependencies**: Corresponds to `WF-Policy-Info` structure in VSAM programs; matches policy-specific sections in `LGCMAREA`.
- **Test Coverage**: Provides comprehensive examples of each policy type with realistic UK-specific data (postcodes, registration numbers, property values).

### Workload Simulation Configuration

#### GENAPP.TXT – Main Workload Simulator Configuration
- Purpose: primary configuration file for IBM Workload Simulator for z/OS (WSim) defining network parameters, transaction paths, and simulation execution profiles.
- Network Configuration:
  - `BUFSIZE=1920`: Terminal buffer size for 3270 data streams
  - `Conrate=No`: Disables connection rate limiting 
  - `DELAY=F1`: Uses F1 delay timing for transaction pacing
  - `LUTYPE=LU2`: Configures for LU Type 2 (3270 terminal) sessions
  - `UTI=100`: Sets utilization target to 100% for maximum throughput
  - `MLOG=YES, MLEN=1000`: Enables message logging with 1000-character limit
  - `OPTIONS=(DEBUG)`: Activates debug mode for detailed execution tracing
- Transaction Paths:
  - `ADDTRANS`: Add-only transaction mix (`SSC1A1`, `SSP1A1`, `SSP2A1`, `SSP3A1`, `SSP4A1`) with 5:1:1:1:1 distribution
  - `ALLTRANS`: Full CRUD transaction mix including inquire, update, and delete operations across all policy types
  - `WEB1`: Web service transaction path (`WSC1I1`, `WSC1A1`) for HTTP-based scenarios
- Terminal Configuration:
  - `GNWS001 VTAMAPPL`: VTAM application identifier for SNA session management
  - `LUSS001 LU`: Logical unit definition with `FRSTTXT=#ONCICS` for CICS connection initialization
  - TCP/IP configuration (commented): Ready for web service simulation via TCP port 4321
- Dependencies: references simulation script files (`SSC1*`, `SSP1*`, `SSP2*`, `SSP3*`, `SSP4*`, `WSC1*`), `#ONCICS` initialization script, and VTAM/CICS connectivity infrastructure.

#### #SSVARS.TXT – Shared Variables and Constants Definition
- Purpose: WSim shared variable definition file providing global constants, counters, and data conversion tables used across all simulation scripts.
- Variable Categories:
  - Runtime Control: `STRT_Debugit`, `STRT_WAS_Route`, `STRT_LU2_Terms`, `STRT_WAS_Terms`, `STRT_Stats_Out` for execution flow control
  - Transaction Counters: Shared integer counters (`Count_lu2_*`, `Count_was_*`) tracking successful transactions per script type (SSC1, SSP1-4 variants)
  - Error Counters: Error tracking counters (`ECount_lu2_*`, `ECount_was_*`) for failed transaction monitoring and reporting
  - Working Variables: Unshared integers (`I1-I5`, `CUST_NUM`, `POL_NUM`, `TRAN_ID`) for temporary calculations and data generation
  - String Variables: Unshared string variables (`S1-S5`, `VS1-VS10`) for dynamic data formatting and screen interaction
- Data Conversion Tables:
  - `E2A`: EBCDIC-to-ASCII conversion table (256-byte hexadecimal constant) for mainframe-to-workstation character translation
  - `A2E`: ASCII-to-EBCDIC conversion table for reverse character translation
- Bit Flags: Control flags (`Found`, `Tran_Error`, `FEmail`) for conditional logic and state management across simulation scenarios
- Dependencies: included by all simulation scripts via `@Include #SSVARS` directive; supports both LU2 (3270 terminal) and WAS (web service) simulation modes.

### Workstation Simulator Transaction Scripts
#### Customer Transaction Scripts (SSC1*)
##### SSC1A1 - Customer Add Simulation
- Purpose: simulates creation of new customer records through the 3270 interface using transaction `SSC1`.
- Flow: navigates to customer add screen, generates random customer data (names from UTBL tables, birth dates, addresses), submits via PF2, validates success message "New Customer Inserted".
- Data Generation: uses UTBL reference tables (`Fname`, `Sname`, `Pcode`) for realistic test data; generates birth dates between 1940-1980, random addresses and postal codes.
- Error Handling: increments `eCount_lu2_SSC1A1` counter on failure, includes optional email notification when transaction count exceeds `STRT_Stats_Out` threshold.
- Dependencies: `#SSVARS` for shared simulation variables, UTBL reference data tables, transaction `SSC1` (maps to `LGACUS01` COBOL program).

##### SSC1I1 - Customer Inquiry Simulation  
- Purpose: simulates customer information retrieval through transaction `SSC1` inquiry function (option 1).
- Flow: first executes `LGCF` to establish customer context, extracts customer number from screen, then performs inquiry via `SSC1` transaction.
- Interface: positions cursor at row 22, column 25 and types '1' to select inquiry option, validates screen response.
- Error Handling: includes counter `Count_lu2_SSC1I1` for performance tracking, debug logging when `STRT_Debugit = 'ON'`.
- Dependencies: requires active customer session context from `LGCF`, transaction `SSC1` (maps to `LGICUS01` COBOL program).

#### Motor Policy Transaction Scripts (SSP1*)
##### SSP1A1 - Motor Policy Add Simulation
- Purpose: simulates motor insurance policy creation through transaction `SSP1` add function.
- Flow: establishes customer context via `LGCF`, extracts customer number, generates comprehensive motor policy data including vehicle details, dates, and premiums.
- Data Generation: creates start/expiry dates (1997-2007), vehicle make/model from UTBL tables (`Cmake`, `Cmodel`), registration numbers, colors (`Ccolor`), values (13000-38000), and manufactured dates (1975-2007).
- Validation: expects success message "New Motor Policy Inserted", logs failure via `eCount_lu2_SSP1A1` counter.
- Dependencies: customer context from `LGCF`, UTBL reference tables for vehicle data, transaction `SSP1` (maps to `LGAPOL01` COBOL program).

##### SSP1I1 - Motor Policy Inquiry Simulation
- Purpose: simulates motor policy information retrieval using policy finder and inquiry functions.
- Flow: uses `LGPF M` command to locate motor policies for customer, extracts policy details from screen, then performs detailed inquiry via `SSP1`.
- Data Extraction: parses screen for policy key format, validates policy type 'M' (Motor), extracts policy and customer numbers for inquiry.
- Error Handling: includes conditional logic to skip inquiry if no motor policy found, tracks performance via `Count_lu2_SSP1I1`.
- Dependencies: `LGPF` policy finder utility, transaction `SSP1` (maps to `LGIPOL01` COBOL program).

##### SSP1U1 - Motor Policy Update Simulation
- Purpose: simulates modification of existing motor policy details through transaction `SSP1` update function (option 4).
- Flow: locates existing motor policy via `LGPF M`, validates "No data" condition, generates updated policy information, submits changes.
- Data Updates: modifies policy dates, vehicle make/model, value, registration, color, premium amounts using randomized data within realistic ranges.
- Validation: expects "Motor Policy Updated" success message, handles update failures via `eCount_lu2_SSP1U1` error counter.
- Dependencies: existing motor policy records, UTBL reference tables, transaction `SSP1` (maps to `LGUPOL01` COBOL program).

##### SSP1D1 - Motor Policy Delete Simulation  
- Purpose: simulates deletion of motor insurance policies through transaction `SSP1` delete function (option 3).
- Flow: uses policy finder to locate motor policy, extracts policy identifiers, performs deletion via option 3.
- Validation: expects "Motor Policy Deleted" confirmation message, logs deletion failures via `eCount_lu2_SSP1D1`.
- Dependencies: existing policy records, `LGPF` policy finder, transaction `SSP1` (maps to `LGDPOL01` COBOL program).

#### Endowment/Life Policy Transaction Scripts (SSP2*)
##### SSP2A1 - Endowment Policy Add Simulation
- Purpose: simulates life insurance policy creation through transaction `SSP2` add function.
- Flow: establishes customer context, generates endowment policy data including beneficiary information, coverage amounts, and policy terms.
- Data Generation: creates policy dates (1997-2007), coverage amounts (10000-999000), beneficiary names from UTBL tables, random Y/N flags for policy options.
- Validation: expects "New Life Policy Inserted" success message, tracks failures via `eCount_lu2_SSP2A1`.
- Dependencies: customer context, UTBL name tables (`Fname`, `Sname`), transaction `SSP2` (maps to `LGAPOL01` COBOL program).

##### SSP2U1 - Endowment Policy Update Simulation
- Purpose: simulates updates to existing endowment policy details.
- Flow: locates endowment policy via `LGPF E`, generates updated beneficiary and coverage information, submits via update option.
- Data Updates: modifies beneficiary names, coverage amounts, policy flags (withholding tax, medical details, etc.) using random data.
- Dependencies: existing endowment policies, transaction `SSP2` (maps to `LGUPOL01` COBOL program).

##### SSP2I1 - Endowment Policy Inquiry Simulation
- Purpose: retrieves endowment policy details through inquiry function.
- Dependencies: `LGPF` policy finder, transaction `SSP2` (maps to `LGIPOL01` COBOL program).

##### SSP2D1 - Endowment Policy Delete Simulation
- Purpose: deletes endowment policies through delete function.
- Dependencies: existing policy records, transaction `SSP2` (maps to `LGDPOL01` COBOL program).

#### House Policy Transaction Scripts (SSP3*)
##### SSP3A1 - House Policy Add Simulation
- Purpose: simulates house insurance policy creation through transaction `SSP3`.
- Flow: establishes customer context, generates house policy data including property details, coverage types, and premiums.
- Data Generation: creates policy dates, house types from UTBL (`Htype`), property values (100000-999000), address information, postal codes from UTBL (`Pcode`).
- Validation: expects "New House Policy Inserted" confirmation message.
- Dependencies: customer context, UTBL reference tables for house data, transaction `SSP3` (maps to `LGAPOL01` COBOL program).

##### SSP3U1 - House Policy Update Simulation  
- Purpose: simulates updates to existing house policy details.
- Flow: locates house policy via `LGPF H`, generates updated property and coverage information.
- Dependencies: existing house policies, transaction `SSP3` (maps to `LGUPOL01` COBOL program).  

##### SSP3I1 - House Policy Inquiry Simulation
- Purpose: retrieves house policy information through inquiry function.
- Dependencies: `LGPF` policy finder, transaction `SSP3` (maps to `LGIPOL01` COBOL program).

##### SSP3D1 - House Policy Delete Simulation
- Purpose: deletes house insurance policies.
- Validation: expects "House Policy Deleted" confirmation message.
- Dependencies: existing policy records, transaction `SSP3` (maps to `LGDPOL01` COBOL program).

#### Commercial Policy Transaction Scripts (SSP4*)  
##### SSP4A1 - Commercial Policy Add Simulation
- Purpose: simulates commercial property insurance policy creation through transaction `SSP4`.
- Flow: generates comprehensive commercial property data including location coordinates, peril coverages, and premium calculations.
- Data Generation: creates property addresses, postal codes, latitude/longitude coordinates, customer names, property types from UTBL (`Ptype`), and detailed peril coverages (Fire, Crime, Flood, Weather) with corresponding premiums.
- Validation: expects "New Commercial Policy Inserted" success message.
- Dependencies: extensive UTBL reference tables, transaction `SSP4` (maps to `LGAPOL01` COBOL program).

##### SSP4I1 - Commercial Policy Inquiry Simulation
- Purpose: retrieves commercial policy details through inquiry function.
- Dependencies: `LGPF` policy finder, transaction `SSP4` (maps to `LGIPOL01` COBOL program).

##### SSP4D1 - Commercial Policy Delete Simulation  
- Purpose: deletes commercial property policies.
- Validation: expects "Commercial Policy Deleted" confirmation message.
- Dependencies: existing policy records, transaction `SSP4` (maps to `LGDPOL01` COBOL program).

#### Data Generation Modules (A2 Scripts)
- **SSC1A2**: customer data generation module providing variables (VS1-VS6) for names, birth dates, addresses, and postal codes used by customer add simulations.
- **SSP1A2**: motor policy data generation module providing variables (VS1-VS10) for customer numbers, policy dates, vehicle details (make/model/color), values, and registration information.
- **SSP2A2**: endowment policy data generation module providing variables for beneficiary names, coverage amounts, policy terms, and flags.
- **SSP3A2**: house policy data generation module providing variables for property details, house types, values, and location information.

#### Simulation Script Architecture
- **Variable Sharing**: all scripts include `#SSVARS` for shared simulation state, counters, and configuration.
- **Data Generation**: extensive use of UTBL reference tables for realistic test data (names, codes, types) and A2 modules for structured variable sets.
- **Error Tracking**: consistent error counter naming (`eCount_lu2_*`) and optional email notification system.
- **Debug Support**: conditional debug logging when `STRT_Debugit = 'ON'`, performance statistics when `STRT_Debugit = 'TEST'`.
- **Screen Automation**: 3270 terminal automation using cursor positioning, field typing, function key transmission, and screen validation.
- **Transaction Integration**: each script maps to corresponding CICS transactions and COBOL programs in the GenApp system.
- **Modular Design**: A1 scripts handle transaction flow and screen interaction, A2 modules provide reusable data generation logic.

### Web Service Simulation Scripts

#### WSC1A1 – SOAP Customer Add Simulation
- Purpose: web service test script for customer creation functionality through SOAP interface to `LGACUS01`.
- Structure: generates complete SOAP envelope with customer data payload and HTTP headers for web service invocation.
- Dependencies: includes `#SSVARS` for shared variables, `SSC1A2` for additional customer data, `WASerror` for error handling routines.
- Data Sources: uses simulation variables (`VS1`, `VS2`, etc.) for synthetic customer names, addresses, and personal details.
- Request Format: constructs `LGACUS01Operation` SOAP message with `01ACUS` request ID and customer demographic fields.
- Notes: targets endpoint `/GENAPP/LGACUS01` with proper SOAP action headers; handles EBCDIC/ASCII translation for mainframe integration.

#### WSC1I1 – SOAP Customer Inquiry Simulation  
- Purpose: web service test script for customer information retrieval through SOAP interface to `LGICUS01`.
- Structure: generates SOAP envelope with inquiry request and random customer number generation for testing.
- Dependencies: includes `#SSVARS` for shared variables, `WASerror` for error handling routines.
- Data Sources: uses `Random(1,10)` function to generate test customer numbers for inquiry operations.
- Request Format: constructs `LGICUS01Operation` SOAP message with `01ICUS` request ID and empty response fields for population.
- Notes: targets endpoint `/GENAPP/LGICUS01`; designed to validate inquiry response structure and data retrieval accuracy.

#### WSLGCF – Customer Validation Web Service  
- Purpose: specialized simulation script for fetching valid customer numbers through `LGICVS01` service interface.
- Structure: builds SOAP request to customer validation service with error detection and response parsing logic.
- Dependencies: relies on `LGICVS01` web service operation for customer number validation and retrieval.
- Error Handling: includes validation logic checking for `<Comma_Data_High>` response elements; signals `StopNow` on validation failures.
- Response Processing: extracts customer number from SOAP response using substring operations and EBCDIC-to-decimal conversion.
- Notes: targets endpoint `/GENAPP/LGICVS01`; includes abort conditions for policy errors and stop signals; provides valid customer numbers for dependent simulation flows.

### Reference Data and Lookup Tables

#### CCOLOR – Car Color Lookup Table
- Purpose: MSGUTBL lookup table providing standard vehicle color options for motor insurance policy simulation.
- Contents: includes 26 color values such as Blue, Purple, Beige, Grey, Orange, Cream, Green, Violet, Indigo, Bronze, Platinum, Azure, Charcoal, Claret, Burgundy, Aqua, Sunburst, Red, White, Silver, Black, Pink, Yellow, Turquoise, Gold, Brown.
- Usage: referenced by simulation scripts and policy creation workflows requiring vehicle color selection.
- Format: standard MSGUTBL structure with descriptive color names suitable for user interface presentation.

#### CMAKE – Car Make Lookup Table  
- Purpose: MSGUTBL lookup table providing standard vehicle manufacturer options for motor insurance policy simulation.
- Contents: includes 21 manufacturer names such as Ford, Mazda, Honda, Cadillac, Ferrari, Hyundai, Peugeot, Renault, Citroen, Land Rover, Mini, Volkswagen, GMC, Vauxhall, Porsche, BMW, Mercedes, Oldsmobile, Toyota, Lada, Skoda.
- Usage: referenced by simulation scripts and policy creation workflows requiring vehicle manufacturer selection.
- Format: standard MSGUTBL structure with manufacturer brand names.

#### CMODEL – Car Model Lookup Table
- Purpose: MSGUTBL lookup table providing standard vehicle model options for motor insurance policy simulation.
- Contents: includes 23 model names such as 205, Twinkle, 911, Riva, Omega, Fiesta, Discovery, Capri, Cortina, Uno, Astra, CRV, Golf, Polo, Z5, Firebird, Thunderbird, Cavalier, 6, Corsa, Boxster, Smallbit, Backseater.
- Usage: referenced by simulation scripts and policy creation workflows requiring vehicle model selection.
- Format: standard MSGUTBL structure with model names ranging from numeric designations to descriptive names.

#### CTYPE – Coverage Type Lookup Table
- Purpose: MSGUTBL lookup table providing standard insurance coverage and risk types for policy simulation.
- Contents: includes 13 coverage types such as Theft, Fire, Accident, Water Damage, Subsidence, Injury, Wind Damage, Vandalism, Weather Damage, Crash, Ice Damage, Death, Serious Illness.
- Usage: referenced by simulation scripts and policy creation workflows requiring coverage type selection across multiple insurance product lines.
- Format: standard MSGUTBL structure with descriptive coverage names suitable for policy documentation.

#### FNAME – First Names Lookup Table
- Purpose: MSGUTBL lookup table providing standard first names for customer data simulation and testing.
- Contents: extensive list of common first names including Adrian, John, Robert, Michael, William, David, Richard, Charles, Joseph, Thomas, Christopher, Daniel, Paul, Mark, Donald, George, Kenneth, Steven, Edward, Brian, Ronald, Anthony, Kevin, Jason, Matthew, Gary, Timothy, and many others.
- Usage: referenced by customer creation and simulation workflows requiring realistic personal name data.
- Format: standard MSGUTBL structure with names formatted for consistent 10-character field width.

#### HTYPE – House Type Lookup Table
- Purpose: MSGUTBL lookup table providing standard residential property types for house insurance policy simulation.
- Contents: includes 17 property types such as Detached, Semi, Bungalow, Flat, Apartment, Farm, B and B, Hotel, Castle, Prison, Garage, Terraced, Mansion, Skip, Condo, Palace, Bedsit.
- Usage: referenced by simulation scripts and house policy creation workflows requiring property type classification.
- Format: standard MSGUTBL structure with property type descriptions.

#### PCODE – Postal Code Lookup Table
- Purpose: MSGUTBL lookup table providing standard UK postal codes for address simulation and geographic testing.
- Contents: extensive list of UK postal codes starting with prefixes like AB (Aberdeen area), including codes such as AB239AB, AB239AF, AB259AB, AB309AA, and hundreds of others covering multiple geographic regions.
- Usage: referenced by customer and property address generation workflows requiring realistic UK postal code data.
- Format: standard MSGUTBL structure with properly formatted UK postal code patterns.

#### PTYPE – Property Type Lookup Table  
- Purpose: MSGUTBL lookup table providing standard commercial property types for business insurance policy simulation.
- Contents: includes 17 property types such as Office, Shop, Retail, Warehouse, Wholesale, Chemist, Park, B & B, Hotel, Prison, Garage, Station, Supermarket, Shopping Mall, Stadium, School, Hospital.
- Usage: referenced by simulation scripts and commercial policy creation workflows requiring business property classification.
- Format: standard MSGUTBL structure with commercial property descriptions.

#### RTYPE – Road Type Lookup Table
- Purpose: MSGUTBL lookup table providing standard street type abbreviations for address formatting in simulation.
- Contents: includes 8 road type entries with both full and abbreviated forms: Road/RD, Street/ST, Avenue/AVE, Close/CL.
- Usage: referenced by address generation workflows requiring proper street type formatting for UK addressing standards.
- Format: standard MSGUTBL structure with both full names and common abbreviations.

#### SNAME – Surname Lookup Table
- Purpose: MSGUTBL lookup table providing standard surnames for customer data simulation and testing.
- Contents: extensive list of common British surnames including Smith, Jones, Taylor, Williams, Brown, Davies, Evans, Wilson, Thomas, Roberts, Johnson, Lewis, Walker, Robinson, Wood, Thompson, White, Watson, Jackson, Wright, Green, Harris, Cooper, King, Lee, Martin, Clarke, and many others.
- Usage: referenced by customer creation and simulation workflows requiring realistic surname data for demographic testing.
- Format: standard MSGUTBL structure with surnames formatted for consistent 10-character field width.

### Simulation Control & Error Handling Assets
#### ONCICS.TXT – CICS Connection Manager  
- Purpose: automated CICS terminal connection recovery and initialization for workload simulation sessions.
- Interfaces: includes `#SSVARS.TXT` for shared variable definitions; monitors screen content for CICS availability indicator `DFHCE3547`.
- Dependencies: workload simulator runtime, `<TORAPPL>` application context, shared `Found` variable from `#SSVARS`.
- Flow Control: uses `onin0001` event handler to detect CICS readiness; suspends terminal for 5-second intervals until connection established; deactivates handler and transmits clear screen once connected.
- Notes: essential bootstrap logic ensuring simulation terminals establish valid CICS session before executing transaction flows; referenced via `C#ONCICS` path in `GENAPP.TXT`.

#### STOP.TXT – Simulation Termination Handler
- Purpose: graceful workload simulator termination with terminal cleanup and resource quiescing.
- Interfaces: includes `#SSVARS.TXT` for environment variables; implements `STOP` message text block for simulator path definitions.
- Dependencies: workload simulator runtime, shared variable context from `#SSVARS`.
- Flow Control: outputs termination message and invokes `Quiesce` command to properly release terminal resources and end simulation session.
- Notes: referenced as `Stop` path in `GENAPP.TXT`; called from transaction scripts (e.g., `SSC1A1.TXT`) to cleanly exit simulation flows.

#### WASERROR.TXT – Web Service Error Handler
- Purpose: specialized error processing for CST SOAP application responses with HTTP status code parsing and application-level error extraction.
- Interfaces: processes web service response data in variable `S5`; outputs diagnostic messages via `MSGTXTID()` function.
- Dependencies: workload simulator string functions (`E2D`, `Substr`, `Pos`, `Char`), web service response parsing context.
- Error Processing Logic: extracts HTTP status code from position 10-12 of response; handles HTTP 200 responses by parsing embedded `<ca_return_code>` XML elements; reports both HTTP-level and application-level error codes with descriptive messages.
- Notes: included via `@Include WASerror` in web service simulation scripts; provides standardized error reporting for SOAP-based transaction testing.

### CICS Event Processing & Monitoring Configuration
#### Transaction_Counters.evbind – Business Transaction Event Binding
- Purpose: CICS Event Processing configuration that captures business transaction metrics and dispatches events to statistics collection program `LGASTAT1`.
- Event Specification: defines `Count_business_trans` event with `Request_Type` (6-byte text) and `Return_code` (2-byte numeric) data fields.
- Capture Configuration: monitors CICS LINK PROGRAM commands targeting programs with names starting with `LG`; captures commarea data at offsets 0-5 (request type) and 6-7 (return code).
- Event Dispatcher: routes captured events to transaction `LGST` which invokes `LGASTAT1` program; uses CCE format for event data exchange; operates with normal priority and non-transactional event processing.
- Integration Points: supports real-time monitoring of GenApp transaction flows (customer/policy operations); provides data feed for statistics dashboard via `LGWEBST5` program and shared TSQ structures.
- Notes: critical monitoring infrastructure enabling transaction throughput measurement and application health tracking; coordinates with named counters (`GENA*` series) for comprehensive workload visibility.

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
