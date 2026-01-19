from generation.railways.train_agent import TrainAgent

def train_agent_limited_flexibility_generator(max_buffer=float("inf"), max_compound_recovery_time=float("inf")):
    class TrainAgentLimitedFlexibility(TrainAgent):
        def calculate_flexibility(self):
            compound_recovery_time = 0.0

            last_buffer_time = max_buffer
            for move in self.route[::-1]:
                local_buffer, local_recovery = self._get_local_flexibility(move)

                # TODO: check order of these operations
                # Because we are going backwards over the route,
                # the buffer time cannot be larger than the buffer time in the future
                # (if ignoring recovery time)
                last_buffer_time = min(last_buffer_time, local_buffer)

                # Buffer time can increase by recovery time if it would fit
                compound_recovery_time += local_recovery
                compound_recovery_time = min(compound_recovery_time, max_compound_recovery_time)
                last_buffer_time = min(last_buffer_time, max_buffer)

                # Store the buffer and crt
                move.add_flexibility(self, last_buffer_time, compound_recovery_time)

    return TrainAgentLimitedFlexibility