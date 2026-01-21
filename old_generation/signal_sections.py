from logging import getLogger
from typing import Union

from old_generation.graph import Edge, TrackGraph, BlockEdge, Direction
import old_generation as generation

logger = getLogger('__main__.' + __name__)

def convertMovesToBlock(moves_per_agent, g: TrackGraph, original_agent=None) -> Union[dict[int, list[BlockEdge]], list[BlockEdge]]:
    block_routes = {}
    signal_tracks = {signal.track for signal in g.signals}
    if original_agent is not None:
        moves_per_agent = {original_agent: moves_per_agent}
    for agent in moves_per_agent:
        logger.debug(f"Converting moves to block for {agent}.")
        block_route = []
        blocks = None
        for move in moves_per_agent[agent]:
            if blocks is None:
                blocks = {block for block in move.to_node.blocks(Direction.SAME) if isinstance(block, generation.graph.Edge)}
            blocks = blocks & {block for block in move.to_node.blocks(Direction.SAME) if isinstance(block, generation.graph.Edge)}
            logger.debug(f"Move: {move}, blocks possible {blocks}")
            if move.to_node in signal_tracks:
                if len(blocks) == 0:
                    raise ValueError(f"No valid block found for last move {move}")
                if len(blocks) > 1:
                    logger.error(f"Should really only be one, {blocks}")
                block_route.append(list(blocks)[0])
                blocks = None
            elif len(blocks) == 0:
                raise ValueError(f"Should really only be one, {blocks}")
        block_routes[agent] = block_route
    if original_agent is not None:
        return block_routes[original_agent]
    return block_routes