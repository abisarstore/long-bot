CREATE OR REPLACE FUNCTION reserve_model_calls(p_model TEXT, p_count INT, p_limit INT)
RETURNS BOOLEAN AS $$
DECLARE
    v_today DATE := CURRENT_DATE;
    v_updated_rows INT;
BEGIN
    -- Ensure row exists
    INSERT INTO model_usage (day, model, used_calls, reserved_calls)
    VALUES (v_today, p_model, 0, 0)
    ON CONFLICT (day, model) DO NOTHING;

    -- Atomic update with limit check
    UPDATE model_usage
    SET reserved_calls = reserved_calls + p_count
    WHERE day = v_today
      AND model = p_model
      AND (used_calls + reserved_calls + p_count) <= p_limit;

    GET DIAGNOSTICS v_updated_rows = ROW_COUNT;
    RETURN v_updated_rows > 0;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION commit_model_calls(p_model TEXT, p_count INT)
RETURNS VOID AS $$
DECLARE
    v_today DATE := CURRENT_DATE;
BEGIN
    UPDATE model_usage
    SET
        reserved_calls = GREATEST(0, reserved_calls - p_count),
        used_calls = used_calls + p_count
    WHERE day = v_today AND model = p_model;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION rollback_model_calls(p_model TEXT, p_count INT)
RETURNS VOID AS $$
DECLARE
    v_today DATE := CURRENT_DATE;
BEGIN
    UPDATE model_usage
    SET reserved_calls = GREATEST(0, reserved_calls - p_count)
    WHERE day = v_today AND model = p_model;
END;
$$ LANGUAGE plpgsql;
