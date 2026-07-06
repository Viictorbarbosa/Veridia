-- ============================================================================
-- Veridia — Scalable Tier Schema
-- ============================================================================
-- Additive migration on top of mvp/schema.sql. Adds session-based routing:
--   - a `sessions` table describing each domain the router can classify into
--   - a `session_id` column on `deltas`, scoping lookups to one session
--   - a `relevance_weight` column, reserved for future in-session ranking
--
-- Design note: `specialty` lives on `sessions`, not on every delta. The
-- original per-delta schema in docs/architecture.md listed it directly, but
-- repeating the same specialty string on every delta in a session is
-- redundant — router.py just needs one row per session to classify against.
-- ============================================================================

CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    specialty    TEXT NOT NULL,   -- natural-language description the router matches questions against
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Ensure a default session exists before backfilling pre-migration deltas into it.
INSERT INTO sessions (session_id, specialty)
VALUES ('default', 'General / unclassified — deltas created before session routing was enabled')
ON CONFLICT (session_id) DO NOTHING;

ALTER TABLE deltas
    ADD COLUMN IF NOT EXISTS session_id TEXT REFERENCES sessions(session_id) ON DELETE SET NULL;

ALTER TABLE deltas
    ADD COLUMN IF NOT EXISTS relevance_weight REAL NOT NULL DEFAULT 1.0;

-- Backfill: any delta inserted before this migration has no session_id yet.
UPDATE deltas SET session_id = 'default' WHERE session_id IS NULL;

-- ============================================================================
-- Indexes
-- ============================================================================
-- The MVP enforced one active delta per causal_key GLOBALLY. At this tier,
-- the same causal_key can legitimately exist in two different sessions
-- (e.g. "timeout" means something different in "auth" vs "billing"), so the
-- uniqueness constraint moves from (causal_key) to (session_id, causal_key).

DROP INDEX IF EXISTS idx_deltas_active_causal_key;

CREATE UNIQUE INDEX IF NOT EXISTS idx_deltas_active_session_causal_key
    ON deltas (session_id, causal_key)
    WHERE active = true;

-- Supports "everything in this session" scans — the core operation this
-- tier exists to make cheap.
CREATE INDEX IF NOT EXISTS idx_deltas_session
    ON deltas (session_id, causal_key);

-- ============================================================================
-- Versioning trigger — upgraded to be session-aware
-- ============================================================================
-- Replaces the MVP's version (same function name, so the existing trigger
-- on `deltas` picks up this new body automatically — no need to touch the
-- trigger definition itself). Without this change, inserting a delta in
-- session A could incorrectly supersede a same-causal_key delta in session B.

CREATE OR REPLACE FUNCTION supersede_previous_delta()
RETURNS TRIGGER AS $$
DECLARE
    prior_id UUID;
BEGIN
    IF NEW.active THEN
        SELECT id INTO prior_id
        FROM deltas
        WHERE causal_key = NEW.causal_key
          AND session_id IS NOT DISTINCT FROM NEW.session_id  -- NULL-safe comparison
          AND active = true
        LIMIT 1;

        IF prior_id IS NOT NULL THEN
            UPDATE deltas SET active = false WHERE id = prior_id;

            IF NEW.previous_version IS NULL THEN
                NEW.previous_version := prior_id;
            END IF;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Convenience view: current truth (unchanged definition — session_id is just
-- another column on it now; callers filter by session_id explicitly)
-- ============================================================================

CREATE OR REPLACE VIEW current_truth AS
SELECT * FROM deltas WHERE active = true;

-- ============================================================================
-- Point-in-time reconstruction — session-scoped overload
-- ============================================================================
-- The MVP's 2-argument truth_as_of(causal_key, as_of) still works for the
-- default/global case. This overload disambiguates when the same causal_key
-- exists in more than one session.

CREATE OR REPLACE FUNCTION truth_as_of(target_session_id TEXT, target_causal_key TEXT, as_of TIMESTAMPTZ)
RETURNS SETOF deltas AS $$
    SELECT *
    FROM deltas
    WHERE causal_key = target_causal_key
      AND session_id IS NOT DISTINCT FROM target_session_id
      AND created_at <= as_of
    ORDER BY created_at DESC
    LIMIT 1;
$$ LANGUAGE sql STABLE;

-- ============================================================================
-- Example (commented out) — same causal_key, two different sessions,
-- demonstrating exactly why uniqueness had to move to (session_id, causal_key)
-- ============================================================================

-- INSERT INTO sessions (session_id, specialty) VALUES
--     ('auth', 'Authentication, sessions, tokens, login/logout behavior'),
--     ('billing', 'Invoices, payments, retries, billing cycles');
--
-- INSERT INTO deltas (causal_key, content, session_id, active) VALUES
--     ('timeout', 'Session timeout triggers automatic logout', 'auth', true),
--     ('timeout', 'Payment retry window times out after 3 attempts', 'billing', true);
--
-- -- Both rows coexist because uniqueness is scoped per session:
-- SELECT session_id, causal_key, content FROM current_truth WHERE causal_key = 'timeout';