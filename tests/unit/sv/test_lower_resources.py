"""Tests for resource acquire/release lowering."""

import pytest
from zuspec.fe.pss.sv.lower_resources import (
    ResourceClaim,
    emit_resource_acquire,
    emit_resource_release,
    emit_resource_domain_constraint,
)


class TestResourceAcquire:
    def test_single_lock(self):
        claims = [ResourceClaim(
            field_name="chan",
            pool_expr="comp.chan_pool",
            id_field="chan_instance_id",
            claim_kind="lock",
        )]
        lines = emit_resource_acquire(claims, "act")
        text = "\n".join(lines)
        assert "comp.chan_pool.lock(act.chan_instance_id);" in text
        assert "act.chan = comp.chan_pool.get(act.chan_instance_id);" in text

    def test_head_action_force_lock(self):
        claims = [ResourceClaim(
            field_name="res",
            pool_expr="comp.res_pool",
            id_field="res_instance_id",
            claim_kind="lock",
            is_head=True,
        )]
        lines = emit_resource_acquire(claims, "act")
        text = "\n".join(lines)
        assert "comp.res_pool.force_lock(act.res_instance_id);" in text

    def test_share_claim(self):
        claims = [ResourceClaim(
            field_name="shared_r",
            pool_expr="comp.shared_pool",
            id_field="shared_r_instance_id",
            claim_kind="share",
        )]
        lines = emit_resource_acquire(claims, "act")
        text = "\n".join(lines)
        assert "comp.shared_pool.try_share(act.shared_r_instance_id);" in text

    def test_head_share(self):
        claims = [ResourceClaim(
            field_name="sr",
            pool_expr="comp.pool",
            id_field="sr_id",
            claim_kind="share",
            is_head=True,
        )]
        lines = emit_resource_acquire(claims, "a")
        text = "\n".join(lines)
        assert "comp.pool.force_share(a.sr_id);" in text

    def test_multiple_claims_canonical_order(self):
        claims = [
            ResourceClaim(field_name="b", pool_expr="comp.pool_b", id_field="b_id"),
            ResourceClaim(field_name="a", pool_expr="comp.pool_a", id_field="a_id"),
        ]
        lines = emit_resource_acquire(claims, "act")
        # pool_a should come before pool_b (sorted by pool_expr)
        lock_lines = [l for l in lines if "lock" in l or "share" in l]
        assert "pool_a" in lock_lines[0]
        assert "pool_b" in lock_lines[1]

    def test_empty_claims(self):
        assert emit_resource_acquire([], "act") == []


class TestResourceRelease:
    def test_single_unlock(self):
        claims = [ResourceClaim(
            field_name="chan",
            pool_expr="comp.chan_pool",
            id_field="chan_instance_id",
            claim_kind="lock",
        )]
        lines = emit_resource_release(claims, "act")
        assert "comp.chan_pool.unlock(act.chan_instance_id);" in lines

    def test_share_release(self):
        claims = [ResourceClaim(
            field_name="sr",
            pool_expr="comp.pool",
            id_field="sr_id",
            claim_kind="share",
        )]
        lines = emit_resource_release(claims, "act")
        assert "comp.pool.unshare(act.sr_id);" in lines

    def test_reverse_order(self):
        claims = [
            ResourceClaim(field_name="a", pool_expr="comp.pool_a", id_field="a_id"),
            ResourceClaim(field_name="b", pool_expr="comp.pool_b", id_field="b_id"),
        ]
        lines = emit_resource_release(claims, "act")
        # Release in reverse of acquisition order (pool_b before pool_a)
        unlock_lines = [l for l in lines if "unlock" in l]
        assert "pool_b" in unlock_lines[0]
        assert "pool_a" in unlock_lines[1]

    def test_empty_claims(self):
        assert emit_resource_release([], "act") == []


class TestDomainConstraint:
    def test_domain_constraint(self):
        claims = [ResourceClaim(
            field_name="r",
            pool_expr="comp.pool",
            id_field="r_id",
        )]
        exprs = emit_resource_domain_constraint(claims, {"comp.pool": 4})
        assert len(exprs) == 1
        assert "r_id inside {[0:3]}" in exprs[0]

    def test_unknown_pool_size(self):
        claims = [ResourceClaim(
            field_name="r",
            pool_expr="comp.pool",
            id_field="r_id",
        )]
        exprs = emit_resource_domain_constraint(claims, {})
        assert len(exprs) == 0
