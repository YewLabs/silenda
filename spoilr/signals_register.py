import collections
import logging
logger = logging.getLogger(__name__)

# Used to separate out hunt-specific logic (e.g. how new puzzles get
# unlocked) from the core mechanic of marking answers as
# correct/incorrect, since we'd like to avoid spoilr calling into hunt
# if reasonably possible

# http://www.eurion.net/python-snippets/snippet/Publish_Subscribe.html
# via pweaver
subscriptions = collections.defaultdict(list)

def register(msg, subscriber):
    subscriptions[msg].append(subscriber)

round_released_message = "round_released_message"
puzzle_released_message = "puzzle_released_message"
puzzle_deleted_message = "puzzle_deleted_message"
puzzle_found_message = "puzzle_found_message"
puzzle_answer_correct_message = "puzzle_answer_correct_message"
interaction_released_message = "interaction_released_message"
metapuzzle_answer_correct_message = "metapuzzle_answer_correct_message"
team_published_message = "team_published_message"
start_team_message = "start_team"
start_all_message = "start_all"
interaction_accomplished_message = "interaction_accomplished"
juice_update_message = "juice_update"
unlock_update_message = "unlock_update"
get_state_message = "get_state_update"
team_log_message = "team_log"
hq_update_message = "hq_update"
