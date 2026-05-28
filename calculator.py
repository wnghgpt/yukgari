import numpy as np

class StrategyCalculator:
    @staticmethod
    def calculate_pyramid(
        channel_top: float,
        channel_bot: float,
        hard_stop_loss: float,
        base_budget: float,
    ):
        if channel_top <= channel_bot:
            raise ValueError("채널 상단 가격은 하단 가격보다 항상 높아야 합니다.")
        if channel_bot <= hard_stop_loss:
            raise ValueError("찐 손절가는 채널 하단보다 낮아야 합니다.")

        dist = channel_top - channel_bot
        channel_width_pct = dist / channel_bot * 100

        if channel_width_pct < 8:
            steps = 3
            weights = [20, 30, 50]
        else:
            steps = 4
            weights = [15, 25, 35, 25]

        # 채널 내 균등 분할 (마지막 진입점 = channel_bot)
        prices = [channel_top - dist * (k / steps) for k in range(1, steps + 1)]

        w_total = sum(weights)
        unit_amount = base_budget / w_total
        amounts = [w * unit_amount for w in weights]

        quantities = [a / p for a, p in zip(amounts, prices)]

        total_qty = sum(quantities)
        total_spent = sum(amounts)
        avg_price = total_spent / total_qty if total_qty > 0 else 0

        risk_per_share = avg_price - hard_stop_loss
        total_risk_amount = risk_per_share * total_qty
        loss_pct = (total_risk_amount / total_spent) * 100 if total_spent > 0 else 0

        zones = []
        for i in range(steps):
            zones.append({
                "price": prices[i],
                "weight": weights[i],
                "allocate_amt": amounts[i],
                "qty": quantities[i]
            })

        return {
            "avg_price": avg_price,
            "hard_stop_loss": hard_stop_loss,
            "total_qty": total_qty,
            "total_spent": total_spent,
            "base_budget": base_budget,
            "steps": steps,
            "weights": weights,
            "channel_width_pct": channel_width_pct,
            "loss_pct": loss_pct,
            "risk_per_share": risk_per_share,
            "total_risk_amount": total_risk_amount,
            "zones": zones
        }

    @staticmethod
    def calculate_rr_targets(avg_price: float, hard_stop_loss: float, rr_multipliers: list[float] = [2, 3, 5, 10]):
        risk = avg_price - hard_stop_loss
        if risk <= 0:
            return {}

        targets = {}
        for rr in rr_multipliers:
            target_price = avg_price + (risk * rr)
            targets[f"RR_{rr}x"] = target_price

        return targets
