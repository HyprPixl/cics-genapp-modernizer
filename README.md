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

## JCL Operations Infrastructure
### Database Setup Jobs (Phase 4 Task 3)
#### DB2CRE.JCL – Database Creation Job
- Purpose: comprehensive DB2 environment setup including storage groups, databases, tablespaces, and all GenApp application tables.
- Dependencies: DB2 subsystem (`<DB2SSID>`), DB2 load libraries (`<DB2HLQ>.SDSNLOAD`), authorization ID (`<SQLID>`), database ID (`<DB2DBID>`).
- Operations: creates storage group `GENASG02`, database `<DB2DBID>`, seven tablespaces (`GENATS01-07`), and tables (`CUSTOMER`, `CUSTOMER_SECURE`, `POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`, `COMMERCIAL`, `CLAIM`).
- Table Structures: supports insurance application with customer demographics, policy hierarchy, and type-specific policy extensions; includes identity columns and timestamp fields.

#### DB2DEL.JCL – Database Cleanup Job  
- Purpose: complete teardown of GenApp DB2 environment for clean reinstallation or environment removal.
- Dependencies: DB2 subsystem, package collection `GENASA1`, plan `GENAONE`, same authorization as creation job.
- Operations: drops all tables in dependency order, removes tablespaces and database, cleans up storage group; frees DB2 packages and plan.
- Notes: handles referential integrity through careful drop sequence; sets `MAXCC=0` to continue despite missing objects.

#### DEFDREP.JCL – CPSM Repository Definition
- Purpose: defines and initializes CPSM (CICSPlex System Manager) repository for centralized CICS resource management.
- Dependencies: CPSM libraries (`<CPSMHLQ>`), CMAS application ID (`<CMASAPPL>`), CMAS system ID (`<CMASYSID>`), WUI application ID (`<WUIAPPL>`).
- Operations: deletes existing `EYUDREP` cluster, creates new VSAM cluster with 500/3000 record allocation, initializes repository with system parameters.
- Configuration: sets timezone, daylight savings, and WUI server connection parameters for CICSPlex management interface.

#### DEFWREP.JCL – WUI Repository Definition
- Purpose: creates VSAM repository for CICS Web User Interface server to support web-based CICS administration.
- Dependencies: WUI application ID (`<WUIAPPL>`), storage class `STANDARD`, VSAM catalog support.
- Operations: removes existing `EYUWREP` cluster, defines new spanned VSAM cluster with 5000 record allocation and 32KB maximum record size.
- Notes: supports variable-length records for web interface metadata; uses large control interval size for performance.

### Workload Simulation Infrastructure (Phase 4 Task 4)
#### ITPENTR.JCL – TPNS Workload Simulator Entry Point
- Purpose: main entry point for running TPNS (Teleprocessing Network Simulator) workload scenarios against CICS GenApp.
- Dependencies: TPNS load library (`<WSIMHLQ>.SITPLOAD`), initialization datasets (`<WSIMWSX>`, `<WSIMMSX>`), log dataset (`<WSIMLGX>`).
- Operations: executes ITPENTER program with GENAPP network configuration; processes simulation scripts and generates performance logs.
- Configuration: supports unlimited region size for large-scale workload simulation; includes dump and print output for diagnostics.

#### ITPLL.JCL – ITP Log List Processor
- Purpose: processes TPNS simulation logs to generate formatted reports and performance analytics.
- Dependencies: SITPLOAD library, simulation log datasets (`<WSIMLGX>`).
- Operations: runs ITPLL program with console formatting, SNA display, and data analysis options; produces formatted simulation reports.
- Output: generates system print output for simulation analysis and performance tuning.

#### ITPSTL.JCL – ITP Script Translation/Compilation
- Purpose: compiles and translates TPNS simulation scripts into executable format for workload testing.
- Dependencies: SITPLOAD library, simulation script library (`<WSIMWSX>`), message library (`<WSIMMSX>`).
- Operations: batch processes simulation scripts including customer (`SSC1*`), policy (`SSP1*-SSP4*`), web service (`WSC1*`) scenarios, and control scripts (`#ONCICS`, `#SSVARS`, `STOP`).
- Script Types: covers complete transaction simulation workflow from CICS startup through individual transaction testing to system shutdown.

#### SAMPCMA.JCL – CICS CICSPlex System Manager Startup
- Purpose: starts CICS CICSPlex System Manager (CPSM) for centralized management of CICS regions and resources.
- Dependencies: CICS libraries (`<CICSHLQ>`), CPSM libraries (`<CPSMHLQ>`), LE runtime (`<CEEHLQ>`), CPSM repository (`EYUDREP`).
- Configuration: enables security, TCP/IP connectivity, and web interface integration; supports unlimited region size and extended memory limits.
- Operations: establishes CICSPlex management context with connection to WUI server for web-based administration.

#### SAMPNCS.JCL – Named Counter Server  
- Purpose: starts CICS Named Counter Server to provide shared numeric counters across CICS regions.
- Dependencies: CICS authentication libraries, counter pool name `GENA`.
- Operations: runs DFHNCMN program to manage shared counters used by GenApp for customer number generation and other sequencing needs.
- Notes: provides centralized counter management for distributed CICS environment; supports customer number assignment in `LGACDB01`.

#### SAMPTSQ.JCL – Shared Temporary Storage Queue Server
- Purpose: starts CICS Shared Temporary Storage Queue server for cross-region temporary storage management.
- Dependencies: CICS authentication libraries, queue pool name `GENA`.
- Configuration: supports 500 maximum queues with 750 buffers for high-volume temporary storage operations.
- Operations: runs DFHXQMN program to provide shared temporary storage services across CICS regions; supports queue sharing for GenApp workloads.

#### SAMPWUI.JCL – Web User Interface Server
- Purpose: starts CICS Web User Interface server to provide web-based administration capabilities for CICSPlex management.
- Dependencies: CICS libraries, CPSM libraries, LE runtime, WUI repository (`EYUWREP`), load library (`<LOADX>`).
- Configuration: enables TCP/IP HTTP host on port 6345, CMCI port 6346, with 3600-second inactive timeout; connects to CICSPlex context.
- Operations: provides web interface for CICS resource management, monitoring, and administration through browser-based tools.

### Web Service Automation Jobs (Phase 4 Task 5)
#### WSA*.JCL Pattern – Language Structure to WSDL Conversion
- Purpose: automated generation of WSDL (Web Services Description Language) files and binding artifacts from COBOL program structures.
- Dependencies: CICS LS2WS procedure (`DFHLS2WS`), Java runtime, source library (`<SOURCEX>`), copybook members, USS file system (`<ZFSHOME>`).
- Pattern: each WSA job processes specific COBOL programs with corresponding SOA interface copybooks to generate web service artifacts.
- Output: generates `.wsdl`, `.wsbind` files, and log files in USS directory structure for web service deployment.

#### WSAAC01.JCL – Customer Add Web Service Generation
- Purpose: generates WSDL and binding artifacts for customer add service (`LGACUS01`) web service interface.
- Programs: processes `LGACUS01` with `SOAIC01` copybook for request/response structures.
- Artifacts: creates `LGACUS01.wsdl`, `LGACUS01.wsbind`, service logs in `/genapp/logs/` and service directory `/genapp/wsdir/`.
- URI: maps to `GENAPP/LGACUS01` web service endpoint for customer creation operations.

#### WSAAP01.JCL – Policy Add Web Service Generation  
- Purpose: generates WSDL artifacts for all policy add operations (`LGAPOL01`) across different policy types.
- Policy Types: creates separate web service definitions for Motor (`SOAIPM1`), House (`SOAIPH1`), Endowment (`SOAIPE1`), and Commercial (`SOAIPB1`) policies.
- Artifacts: generates type-specific WSDL files (`LGAPOLM1.wsdl`, `LGAPOLH1.wsdl`, `LGAPOLE1.wsdl`, `LGAPOLB1.wsdl`) with corresponding binding files.
- URIs: maps to policy-type-specific endpoints (`GENAPP/LGAPOLM1`, `GENAPP/LGAPOLH1`, etc.) for targeted policy creation.

#### WSAIC01.JCL – Customer Inquiry Web Service Generation
- Purpose: generates WSDL and binding artifacts for customer inquiry service (`LGICUS01`) web service interface.
- Programs: processes `LGICUS01` with `SOAIC01` copybook for customer lookup request/response structures.
- Artifacts: creates `LGICUS01.wsdl`, `LGICUS01.wsbind`, and service logs for customer inquiry web service.
- URI: maps to `GENAPP/LGICUS01` web service endpoint for customer information retrieval operations.

#### WSAIP01.JCL – Policy Inquiry Web Service Generation
- Purpose: generates WSDL artifacts for all policy inquiry operations (`LGIPOL01`) across different policy types and special mobile interface.
- Policy Types: creates separate web service definitions for Motor, House, Endowment, and Commercial policy inquiries; includes special mobile sample interface (`IPPROGMB`).
- Copybooks: uses policy-type-specific copybooks (`SOAIPM1`, `SOAIPH1`, `SOAIPE1`, `SOAIPB1`) and mobile lookup copybooks (`POLLOOK`, `POLLOO2`).
- URIs: maps to policy-type-specific inquiry endpoints and mobile interface (`GENAPP/LGIPOL02`) for multi-record policy lookups.

#### WSAUC01.JCL – Customer Update Web Service Generation
- Purpose: generates WSDL and binding artifacts for customer update service (`LGUCUS01`) web service interface.
- Programs: processes `LGUCUS01` with `SOAIC01` copybook for customer update request/response structures.
- Artifacts: creates `LGUCUS01.wsdl`, `LGUCUS01.wsbind`, and service logs for customer modification web service.
- URI: maps to `GENAPP/LGUCUS01` web service endpoint for customer profile update operations.

#### WSAUP01.JCL – Policy Update Web Service Generation
- Purpose: generates WSDL artifacts for all policy update operations (`LGUPOL01`) across different policy types.
- Policy Types: creates separate web service definitions for Motor, House, Endowment, and Commercial policy updates.
- Artifacts: generates type-specific WSDL files (`LGUPOLM1.wsdl`, `LGUPOLH1.wsdl`, `LGUPOLE1.wsdl`, `LGUPOLB1.wsdl`) with corresponding binding files.
- URIs: maps to policy-type-specific update endpoints (`GENAPP/LGUPOLM1`, etc.) for targeted policy modification operations.

#### WSAVC01.JCL – Customer VSAM Web Service Generation
- Purpose: generates WSDL and binding artifacts for customer VSAM lookup service (`LGICVS01`) for direct VSAM file access.
- Programs: processes `LGICVS01` with VSAM-specific copybooks (`SOAVCII`, `SOAVCIO`) for VSAM customer file operations.
- Artifacts: creates `LGICVS01.wsdl`, `LGICVS01.wsbind`, and service logs for VSAM customer lookup web service.
- URI: maps to `GENAPP/LGICVS01` web service endpoint for direct customer VSAM file access.

#### WSAVP01.JCL – Policy VSAM Web Service Generation
- Purpose: generates WSDL and binding artifacts for policy VSAM lookup service (`LGIPVS01`) for direct VSAM file access.
- Programs: processes `LGIPVS01` with VSAM-specific copybooks (`SOAVPII`, `SOAVPIO`) for VSAM policy file operations.
- Artifacts: creates `LGIPVS01.wsdl`, `LGIPVS01.wsbind`, and service logs for VSAM policy lookup web service.  
- URI: maps to `GENAPP/LGIPVS01` web service endpoint for direct policy VSAM file access.

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
