"""
Recreate hordak views after hordak 0055 alters the credit/debit column types.

This migration depends on both our drop-views migration (0002) and hordak 0055,
ensuring it only runs after both are complete. The views are recreated with the
same SQL as in hordak 0052 — they are compatible with the updated column types.
"""

from django.db import migrations

RECREATE_LEG_VIEW_SQL = """
CREATE VIEW hordak_leg_view AS (
    SELECT
        L.id,
        L.uuid,
        transaction_id,
        account_id,
        A.full_code  AS account_full_code,
        A.name       AS account_name,
        A.type       AS account_type,
        T.date       AS date,
        L.credit,
        L.debit,
        COALESCE(L.debit, L.credit)      AS amount,
        L.currency,
        COALESCE(L.debit * -1, L.credit) AS legacy_amount,
        (CASE WHEN L.debit IS NULL THEN 'CR' ELSE 'DR' END) AS type,
        (
            CASE WHEN A.lft = A.rght - 1
            THEN SUM(COALESCE(credit, 0)::DECIMAL - COALESCE(debit, 0)::DECIMAL)
                 OVER (PARTITION BY account_id, currency ORDER BY T.date, L.id)
            END
        ) AS account_balance,
        T.description AS transaction_description,
        L.description AS leg_description
    FROM hordak_leg L
    INNER JOIN hordak_transaction T ON L.transaction_id = T.id
    INNER JOIN hordak_account     A ON A.id = L.account_id
    ORDER BY T.date DESC, id DESC
);
"""

RECREATE_TRANSACTION_VIEW_SQL = """
CREATE OR REPLACE VIEW hordak_transaction_view AS (
    SELECT
        T.*,
        (
            SELECT JSONB_AGG(L_CR.account_id)
            FROM hordak_leg L_CR
            INNER JOIN hordak_account A ON A.id = L_CR.account_id
            WHERE L_CR.transaction_id = T.id AND L_CR.credit IS NOT NULL
        ) AS credit_account_ids,
        (
            SELECT JSONB_AGG(L_DR.account_id)
            FROM hordak_leg L_DR
            INNER JOIN hordak_account A ON A.id = L_DR.account_id
            WHERE L_DR.transaction_id = T.id AND L_DR.debit IS NOT NULL
        ) AS debit_account_ids,
        (
            SELECT JSONB_AGG(A.name)
            FROM hordak_leg L_CR
            INNER JOIN hordak_account A ON A.id = L_CR.account_id
            WHERE L_CR.transaction_id = T.id AND L_CR.credit IS NOT NULL
        ) AS credit_account_names,
        (
            SELECT JSONB_AGG(A.name)
            FROM hordak_leg L_DR
            INNER JOIN hordak_account A ON A.id = L_DR.account_id
            WHERE L_DR.transaction_id = T.id AND L_DR.debit IS NOT NULL
        ) AS debit_account_names,
        JSONB_AGG(jsonb_build_object('amount', L.credit, 'currency', L.currency)) AS amount
    FROM hordak_transaction T
    INNER JOIN LATERAL (
        SELECT SUM(credit) AS credit, currency
        FROM hordak_leg L
        WHERE L.transaction_id = T.id AND L.credit IS NOT NULL
        GROUP BY currency
    ) L ON TRUE
    GROUP BY T.id, T.uuid, T.timestamp, T.date, T.description
    ORDER BY T.id DESC
);
"""

DROP_VIEWS_SQL = """
DROP VIEW IF EXISTS hordak_leg_view;
DROP VIEW IF EXISTS hordak_transaction_view;
"""


class Migration(migrations.Migration):
    """
    Recreate hordak views after hordak 0055 has altered the credit/debit column types.

    The view definitions are identical to those created by hordak 0052 and remain
    compatible with the updated column types introduced by hordak 0055.
    """

    dependencies = [
        ("companies", "0002_pre_hordak_0055_drop_views"),
        ("hordak", "0055_alter_leg_credit_alter_leg_currency_alter_leg_debit"),
    ]

    operations = [
        migrations.RunSQL(
            sql=RECREATE_LEG_VIEW_SQL + RECREATE_TRANSACTION_VIEW_SQL,
            reverse_sql=DROP_VIEWS_SQL,
        ),
    ]
