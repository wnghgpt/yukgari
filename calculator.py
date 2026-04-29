import numpy as np

class StrategyCalculator:
    @staticmethod
    def calculate_pyramid(
        channel_top: float,
        channel_bot: float,
        hard_stop_loss: float,
        base_budget: float,
        weights: list[float]  # [w1, w2, w3, w4] 반드시 4개여야 함
    ):
        """
        채널 박스권 4단 분할 매수 전략:
        1~3차 비중은 base_budget 내에서 100% 소진.
        4차 비중은 추가(비상금) 시드로 오버 부킹.
        """
        if channel_top <= channel_bot:
            raise ValueError("채널 상단 가격은 하단 가격보다 항상 높아야 합니다.")
        if channel_bot <= hard_stop_loss:
            raise ValueError("찐 손절가는 채널 하단보다 낮아야 합니다.")
            
        dist = channel_top - channel_bot
        
        # 기하학적 4단 진입 타점 계산 (승률 극대화 커스텀 셋업)
        p1 = channel_top - (dist * 0.30)      # 1차: 30% 지점
        p2 = channel_top - (dist * 0.60)      # 2차: 60% 지점
        p3 = channel_top - (dist * 0.90)      # 3차: 90% 지점
        p4 = hard_stop_loss * 1.01            # 찐손절 방어선 (투매 줍기 비상금)
        prices = [p1, p2, p3, p4]
        
        # 자금 분배 계산 (1~4차 모두 base_budget 내에서 비율대로 소진)
        w_total = sum(weights)
        if w_total <= 0: raise ValueError("매수 비중의 합은 0보다 커야 합니다.")
        
        unit_amount = base_budget / w_total
        
        amounts = [
            weights[0] * unit_amount,
            weights[1] * unit_amount,
            weights[2] * unit_amount,
            weights[3] * unit_amount
        ]
        
        quantities = [a / p for a, p in zip(amounts, prices)]
        
        total_qty = sum(quantities)
        total_spent = sum(amounts) # 예산(base) + 4차 비상금
        avg_price = total_spent / total_qty if total_qty > 0 else 0
        
        # 리스크 및 손실률 산출 (4차까지 전부 뚫려서 강제 찐손절 당했을 경우의 최대 타격액)
        risk_per_share = avg_price - hard_stop_loss
        total_risk_amount = risk_per_share * total_qty
        loss_pct = (total_risk_amount / total_spent) * 100 if total_spent > 0 else 0
        
        # 쪼개진 존 세부 내역
        zones = []
        for i in range(4):
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
            "extra_budget": 0,
            "loss_pct": loss_pct,
            "risk_per_share": risk_per_share,
            "total_risk_amount": total_risk_amount,
            "zones": zones
        }

    @staticmethod
    def calculate_rr_targets(avg_price: float, hard_stop_loss: float, rr_multipliers: list[float] = [2, 3, 5, 10]):
        """
        예상 평단가와 리스크(손절 폭)를 기준으로 RR 목표가를 산출합니다.
        """
        risk = avg_price - hard_stop_loss
        if risk <= 0:
            return {}
            
        targets = {}
        for rr in rr_multipliers:
            target_price = avg_price + (risk * rr)
            targets[f"RR_{rr}x"] = target_price
            
        return targets
