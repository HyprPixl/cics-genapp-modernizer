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

## Shared Copybooks & Maps
### LGCMAREA – Core Communication Area Structure
- Purpose: central commarea structure used by all GenApp transaction programs to standardize inter-program communication and data exchange.
- Structure: 32,500-byte flexible layout with 28-byte header (`CA-REQUEST-ID`, `CA-RETURN-CODE`, `CA-CUSTOMER-NUM`) plus polymorphic payload section `CA-REQUEST-SPECIFIC` that redefined for different operation types.
- Customer Operations: `CA-CUSTOMER-REQUEST` redefine provides customer profile fields (name, DOB, address, phone, email) plus variable policy data area.
- Customer Security: `CA-CUSTSECR-REQUEST` redefine handles authentication with encrypted password, change count, and security state indicator.
- Policy Operations: `CA-POLICY-REQUEST` redefine includes policy number and common policy details (dates, broker info, payment) with type-specific sections for Endowment, House, Motor, Commercial, and Claim data.
- Usage Pattern: all front-end transaction programs (`*01`) validate commarea length and structure before delegating to corresponding backend services; enables consistent error handling and request/response formatting across the application.

### LGPOLICY – Database Field Definitions
- Purpose: comprehensive DB2 host variable definitions and length constants used by database service programs for consistent field mapping and validation.
- Length Constants: `WS-POLICY-LENGTHS` section defines computed field lengths for all policy types (Customer: 72, Policy: 72, Endowment: 52, House: 58, Motor: 65, Commercial: 1102, Claim: 546 bytes) plus full record lengths for commarea validation.
- Database Structures: mirrors DB2 table schemas with `DB2-CUSTOMER`, `DB2-POLICY`, `DB2-ENDOWMENT`, `DB2-HOUSE`, `DB2-MOTOR`, `DB2-COMMERCIAL`, and `DB2-CLAIM` sections providing exact field definitions for SQL operations.
- Field Alignment: ensures COBOL data types and lengths match corresponding DB2 column definitions to prevent data truncation or type conversion errors during database operations.
- Dependencies: used by all database backend services (`*DB01` programs) for SQL host variable declarations and by frontend programs for commarea length validation calculations.

### POLLOOK & POLLOO2 – Policy Lookup Structures
- Purpose: simplified commarea structures for lightweight policy lookup operations, particularly in batch processing and inquiry scenarios.
- POLLOOK: basic 3-field structure with request ID (6 chars), customer number (10 digits), and general request-specific data (32,482 bytes) for simple customer-based policy queries.
- POLLOO2: specialized structure for multi-policy customer scenarios with `CA-CUSPOL-REQUEST` containing array of 5 policy entries, each with policy number and type indicator, plus additional policy data area.
- Usage: primarily used in policy inquiry and customer summary operations where full `LGCMAREA` structure would be unnecessarily complex; enables efficient policy enumeration and selective data retrieval.

### SOA Interface Copybooks – Service Integration Structures
#### SOAIC01 – Customer Service Interface
- Purpose: customer-focused SOA service interface providing streamlined customer data exchange with reduced payload size (30KB vs 32KB) for web service compatibility.
- Structure: standard header fields (`CA-REQUEST-ID`, `CA-RETURN-CODE`, `CA-CUSTOMER-NUM`) followed by complete customer profile (name, DOB, address, contact info) and compact policy data area.
- Usage: designed for customer inquiry and update operations in service-oriented architecture scenarios where payload size constraints apply.

#### SOAIPB1 – Commercial Policy Interface
- Purpose: commercial policy-specific interface optimized for business insurance operations with comprehensive property and risk assessment data.
- Structure: standard header plus policy common fields (dates, broker, payment) followed by complete commercial policy details (address, coordinates, property type, peril coverage, premiums, status).
- Risk Management: includes detailed peril coverage fields (Fire, Crime, Flood, Weather) with separate risk assessment and premium calculation areas for complex commercial underwriting.

#### SOAIPE1 – Endowment Policy Interface
- Purpose: life insurance and investment product interface supporting endowment policy operations with fund management and assurance details.
- Structure: standard header plus policy basics extended with endowment-specific fields (with-profits indicator, equities, managed fund selection, term, sum assured, life assured details).
- Investment Focus: designed for life insurance products with investment components requiring fund selection and profit-sharing configuration.

#### SOAIPH1 – House Policy Interface
- Purpose: residential property insurance interface optimized for home insurance operations with property valuation and location details.
- Structure: standard header plus policy common data followed by house-specific fields (property type, bedrooms, value, address components).
- Property Details: includes comprehensive residential property information for underwriting and risk assessment of domestic insurance policies.

#### SOAIPM1 – Motor Policy Interface
- Purpose: vehicle insurance interface supporting comprehensive motor insurance operations with vehicle specifications and claim history.
- Structure: standard header plus policy basics extended with motor-specific details (make, model, value, registration, color, engine size, manufacturing date, premium, accident history).
- Vehicle Focus: provides complete vehicle profile for motor insurance underwriting, premium calculation, and claim management operations.

### SOA Data Exchange Copybooks – Validation & Communication
#### SOAVCII – Customer Input Validation
- Purpose: minimal input validation structure for customer operations providing basic customer number input with buffer space for service validation routines.
- Structure: simple 2-field layout with customer number (10 chars) and 72-byte buffer for validation data or error information.

#### SOAVCIO – Customer Output Communication
- Purpose: compact customer output structure for service responses with text message and high-level status indicator fields.
- Structure: 3-field layout with descriptive text (14 chars), high-priority indicator (10 chars), and 48-byte filler for additional response data.

#### SOAVPII – Policy Input Validation
- Purpose: policy lookup input structure designed for policy number validation services with policy type discrimination capability.
- Structure: minimal 3-field layout with policy type indicator (1 char), customer number (10 digits), and 79-byte buffer for additional validation parameters.

#### SOAVPIO – Policy Output Communication
- Purpose: policy lookup output structure providing policy identification results with key information for downstream processing.
- Structure: response format with descriptive text (11 chars), composite key containing policy type and numbers (customer: 10 digits, policy: 10 digits), and 48-byte buffer for additional output data.

### SSMAP.BMS – Screen Layout Definitions
- Purpose: BMS mapset defining 3270 terminal screen layouts for customer and policy management transactions, providing standardized user interface across all GenApp operations.
- Screen Types: supports multiple transaction screens including customer menu (SSMAPC1), motor policy menu (SSMAPP1), and additional policy type screens for complete transaction coverage.

#### Customer Screen (SSMAPC1)
- Layout: 24x80 character screen with title 'General Insurance Customer Menu' and menu options for customer inquiry (1), add (2), and update (4) operations.
- Input Fields: customer number (10 digits, right-justified with zero fill), customer name (first: 10 chars, last: 20 chars), date of birth (10 chars with yyyy-mm-dd format), address components (house name: 20 chars, number: 4 chars, postcode: 8 chars), phone numbers (home/mobile: 20 chars each), and email address (27 chars).
- Navigation: option selection field (1 character, numeric, required entry) and error message area (40 characters) for user feedback and validation messages.

#### Motor Policy Screen (SSMAPP1)
- Layout: 24x80 character screen with title 'General Insurance Motor Policy Menu' supporting policy inquiry (1), add (2), delete (3), and update (4) operations.
- Policy Fields: policy number (10 digits, right-justified), customer number (10 digits), issue and expiry dates (10 chars each with yyyy-mm-dd format), vehicle details including make, model, value, registration, color, engine capacity, manufacturing date, premium amounts, and accident history.
- Data Entry: comprehensive vehicle information capture supporting complete motor insurance underwriting with validation and formatting requirements for numeric and date fields.

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
