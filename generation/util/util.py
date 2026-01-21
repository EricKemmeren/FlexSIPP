from logging import getLogger

logger = getLogger('__main__.' + __name__)

a_to_s = {
    "4.5": 40,
    "7": 40,
    "8": 40,
    "9": 40,
    "10": 40,
    "12": 60,
    "15": 80,
    "18": 80,
    "18.5": 80,
    "20": 125,
    "29": 140,
    "34.7": 140,
    "39.1": 160
}
def angle_to_speed(angle):
    if angle is None:
        return 360 / 3.6
    return a_to_s[angle] / 3.6


def print_node_intervals_per_train(node_intervals, edge_intervals, g, move=None):
    ### log the intervals
    if move:
        logger.info(f"\nMove from {move['startLocation']} to {move['endLocation']}\nUNSAFE INTERVALS\n")
    for train in node_intervals:
        logger.info(f"=====Train {train}======")
        for n in node_intervals[train]:
            if len(node_intervals[train][n]) > 0:
                logger.info(f"Node {n} has {len(node_intervals[train][n])} intervals:")
                for x in node_intervals[train][n]:
                    logger.info(f"    <{x[0]},{x[1]}>")
                for e in g.nodes[n].outgoing:
                    if len(edge_intervals[train][e.get_identifier()]) > 0:
                        logger.info(f"    Edge {e.get_identifier()} has {len(edge_intervals[train][e.get_identifier()])} intervals:")
                        for x in edge_intervals[train][e.get_identifier()]:
                            logger.info(x)
    logger.info("END\n\n")