from .base import MarketView, DirectionOutput, MomentumOutput, SignalStack
from .direction import score_direction
from .momentum  import score_momentum

def compute_signal_stack(view: MarketView) -> SignalStack:
    return SignalStack(
        pair=view.pair, session=view.session, timestamp=view.timestamp,
        direction=score_direction(view),
        momentum=score_momentum(view),
    )
