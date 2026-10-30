# Architecture and assumptions

Master data -> weekly forecasts + inventory + inbound POs -> chronological balance projection -> shortage records -> candidate mitigation records -> manifest and tests.

Balance(t) = Balance(t-1) + OnTimeInbound(t) - Demand(t).

A negative balance carries forward as backlog, not a physical negative stock count. Production is not yet implemented. POs arrive in their expected-arrival ISO week. No partial receipts or cancellations are modeled. Candidate mitigations are illustrative, not approved decisions.

Primary keys are immutable string IDs; each dependent table carries named parent IDs. A full schema/cardinality/effective-date reference remains to be built.
