import random
import math
from .base import BasePathfinding


class PSO_GA(BasePathfinding):
    """
    Hybrid PSO-GA algorithm for pathfinding.
    
    Combines Particle Swarm Optimization with Genetic Algorithm operators:
    - PSO for global exploration and convergence
    - GA crossover for combining good solutions
    - GA mutation for diversity maintenance
    - Selection pressure for fitness-based evolution
    """

    def __init__(self, nodes, connections):
        super().__init__(nodes, connections)
        self.graph = self._build_graph(connections)
        
        # Population parameters
        self.population_size = 40
        self.max_iterations = 100
        
        # PSO parameters
        self.w = 0.7  # Inertia weight
        self.c1 = 1.4  # Cognitive (personal best)
        self.c2 = 1.4  # Social (global best)
        
        # GA parameters
        self.crossover_rate = 0.7
        self.mutation_rate = 0.2
        self.elite_size = 2  # Number of best solutions to preserve

    def _build_graph(self, connections):
        """Build adjacency graph from connections."""
        graph = {node: {} for node in self.nodes}
        for conn in connections:
            node1, node2, distance = conn["node1"], conn["node2"], conn["distance"]
            graph[node1][node2] = distance
            graph[node2][node1] = distance
        return graph

    def find_shortest_path(self, start, end):
        """
        Find path using hybrid PSO-GA algorithm.
        
        Args:
            start: Starting node
            end: Destination node
            
        Returns:
            list: Path from start to end, or empty list if no path found
        """
        if start == end:
            return [start]

        if start not in self.graph or end not in self.graph:
            return []

        # Initialize population (particles)
        population = self._initialize_population(start, end)
        
        # Track global best
        global_best = None
        global_best_fitness = float('inf')

        for iteration in range(self.max_iterations):
            # Evaluate fitness for all individuals
            fitness_scores = []
            for individual in population:
                fitness = self._evaluate_fitness(individual['position'])
                individual['fitness'] = fitness
                fitness_scores.append(fitness)
                
                # Update personal best
                if fitness < individual['best_fitness']:
                    individual['best_position'] = individual['position'].copy()
                    individual['best_fitness'] = fitness
                
                # Update global best
                if fitness < global_best_fitness:
                    global_best = individual['position'].copy()
                    global_best_fitness = fitness

            # Early termination if we found a valid path
            if global_best and self._is_valid_path(global_best, start, end):
                if iteration > 10:  # Allow some iterations for optimization
                    break

            # Apply hybrid operators
            population = self._evolve_population(population, global_best, start, end)

        # Return the best path found
        if global_best and self._is_valid_path(global_best, start, end):
            return self._clean_path(global_best, start, end)
        
        # Fallback to greedy if hybrid algorithm fails
        return self._greedy_fallback(start, end)

    def _initialize_population(self, start, end):
        """Initialize population with diverse paths."""
        population = []
        for i in range(self.population_size):
            # Use different strategies for diversity
            if i < self.population_size // 2:
                path = self._generate_random_path(start, end)
            else:
                path = self._generate_greedy_path(start, end)
            
            individual = {
                'position': path,
                'velocity': [],
                'best_position': path.copy(),
                'best_fitness': self._evaluate_fitness(path),
                'fitness': float('inf')
            }
            population.append(individual)
        return population

    def _generate_random_path(self, start, end, max_length=20):
        """Generate a random path from start to end."""
        path = [start]
        current = start
        visited = {start}
        
        for _ in range(max_length):
            if current == end:
                break
                
            neighbors = [n for n in self.graph[current].keys() if n not in visited]
            
            if not neighbors:
                if end in self.graph[current]:
                    path.append(end)
                break
            
            next_node = random.choice(neighbors)
            path.append(next_node)
            visited.add(next_node)
            current = next_node
        
        return path

    def _generate_greedy_path(self, start, end):
        """Generate a greedy path (nearest neighbor)."""
        path = [start]
        current = start
        visited = {start}
        
        while current != end and len(path) < len(self.nodes):
            neighbors = [
                (n, self.graph[current][n])
                for n in self.graph[current].keys()
                if n not in visited
            ]
            
            if not neighbors:
                break
            
            # Pick nearest neighbor
            next_node = min(neighbors, key=lambda x: x[1])[0]
            path.append(next_node)
            visited.add(next_node)
            current = next_node
        
        return path

    def _evaluate_fitness(self, path):
        """
        Calculate fitness (lower is better).
        Fitness = path_cost + penalties
        """
        if not path or len(path) < 2:
            return float('inf')
        
        cost = 0
        invalid_connections = 0
        
        for i in range(len(path) - 1):
            node1, node2 = path[i], path[i + 1]
            
            if node2 in self.graph.get(node1, {}):
                cost += self.graph[node1][node2]
            else:
                # Heavy penalty for invalid connections
                invalid_connections += 1
                cost += 1000
        
        # Additional penalties
        path_length_penalty = len(path) * 0.1  # Prefer shorter paths
        
        return cost + path_length_penalty + (invalid_connections * 500)

    def _evolve_population(self, population, global_best, start, end):
        """Apply hybrid PSO-GA operators to evolve population."""
        new_population = []
        
        # Sort by fitness
        population.sort(key=lambda x: x['fitness'])
        
        # Elitism: Keep best individuals
        for i in range(self.elite_size):
            new_population.append(population[i])
        
        # Generate rest of population
        while len(new_population) < self.population_size:
            # Apply PSO update
            if random.random() < 0.5:
                parent = random.choice(population[:self.population_size // 2])
                offspring = self._pso_update(parent, global_best)
            else:
                # Apply GA crossover
                if random.random() < self.crossover_rate:
                    parent1 = self._tournament_selection(population)
                    parent2 = self._tournament_selection(population)
                    offspring = self._crossover(parent1, parent2, start, end)
                else:
                    offspring = random.choice(population)
            
            # Apply GA mutation
            if random.random() < self.mutation_rate:
                offspring = self._mutate(offspring, start, end)
            
            new_population.append(offspring)
        
        return new_population

    def _pso_update(self, particle, global_best):
        """Update particle position using PSO equations."""
        new_particle = {
            'position': particle['position'].copy(),
            'velocity': particle['velocity'].copy(),
            'best_position': particle['best_position'].copy(),
            'best_fitness': particle['best_fitness'],
            'fitness': particle['fitness']
        }
        
        # PSO velocity update (adapted for discrete paths)
        if random.random() < self.w:
            # Inertia: keep current path
            pass
        
        if random.random() < self.c1:
            # Cognitive: move toward personal best
            self._move_toward(new_particle['position'], particle['best_position'])
        
        if random.random() < self.c2 and global_best:
            # Social: move toward global best
            self._move_toward(new_particle['position'], global_best)
        
        return new_particle

    def _tournament_selection(self, population, tournament_size=3):
        """Select individual using tournament selection."""
        tournament = random.sample(population, min(tournament_size, len(population)))
        return min(tournament, key=lambda x: x['fitness'])

    def _crossover(self, parent1, parent2, start, end):
        """
        Perform order crossover (OX) between two parents.
        Preserves relative order of nodes from parents.
        """
        path1 = parent1['position']
        path2 = parent2['position']
        
        if len(path1) < 2 or len(path2) < 2:
            return parent1
        
        # Find common nodes
        common = set(path1) & set(path2)
        
        if len(common) < 2:
            # Not enough common nodes, return better parent
            return parent1 if parent1['fitness'] < parent2['fitness'] else parent2
        
        # Create offspring by combining paths
        offspring_path = [start]
        current = start
        visited = {start}
        
        # Alternate between parents' choices
        use_parent1 = True
        max_steps = len(self.nodes)
        
        for _ in range(max_steps):
            if current == end:
                break
            
            source_path = path1 if use_parent1 else path2
            next_node = None
            
            # Find next unvisited node from source path
            for node in source_path:
                if node not in visited and node in self.graph.get(current, {}):
                    next_node = node
                    break
            
            # If no node found, try other parent
            if not next_node:
                source_path = path2 if use_parent1 else path1
                for node in source_path:
                    if node not in visited and node in self.graph.get(current, {}):
                        next_node = node
                        break
            
            # If still no node, pick any valid neighbor
            if not next_node:
                neighbors = [n for n in self.graph[current].keys() if n not in visited]
                if neighbors:
                    next_node = random.choice(neighbors)
                else:
                    break
            
            offspring_path.append(next_node)
            visited.add(next_node)
            current = next_node
            use_parent1 = not use_parent1
        
        return {
            'position': offspring_path,
            'velocity': [],
            'best_position': offspring_path.copy(),
            'best_fitness': self._evaluate_fitness(offspring_path),
            'fitness': float('inf')
        }

    def _mutate(self, individual, start, end):
        """Apply mutation operators to individual."""
        path = individual['position'].copy()
        
        if len(path) < 3:
            return individual
        
        mutation_type = random.random()
        
        if mutation_type < 0.33:
            # Swap mutation
            i, j = random.sample(range(1, len(path) - 1), 2)
            path[i], path[j] = path[j], path[i]
        
        elif mutation_type < 0.66:
            # Insert mutation: insert a random valid node
            if len(path) < len(self.nodes):
                insert_pos = random.randint(1, len(path) - 1)
                prev_node = path[insert_pos - 1]
                next_node = path[insert_pos]
                
                # Find nodes connected to both prev and next
                candidates = []
                for node in self.graph[prev_node].keys():
                    if node not in path and next_node in self.graph.get(node, {}):
                        candidates.append(node)
                
                if candidates:
                    path.insert(insert_pos, random.choice(candidates))
        
        else:
            # Reverse mutation: reverse a subsequence
            if len(path) > 3:
                i = random.randint(1, len(path) - 3)
                j = random.randint(i + 1, len(path) - 1)
                path[i:j+1] = reversed(path[i:j+1])
        
        return {
            'position': path,
            'velocity': [],
            'best_position': path.copy(),
            'best_fitness': self._evaluate_fitness(path),
            'fitness': float('inf')
        }

    def _move_toward(self, current_path, target_path):
        """Move current path toward target path."""
        if not current_path or not target_path or len(current_path) < 2:
            return
        
        # Try to incorporate nodes from target path
        for i in range(min(len(current_path), len(target_path))):
            if i < len(target_path) and target_path[i] in current_path:
                idx = current_path.index(target_path[i])
                if idx != i:
                    current_path[i], current_path[idx] = current_path[idx], current_path[i]

    def _is_valid_path(self, path, start, end):
        """Check if path is valid."""
        if not path or len(path) < 2:
            return False
        
        if path[0] != start or path[-1] != end:
            return False
        
        # Check all connections exist
        for i in range(len(path) - 1):
            if path[i + 1] not in self.graph.get(path[i], {}):
                return False
        
        return True

    def _clean_path(self, path, start, end):
        """Clean and validate the path."""
        cleaned = []
        seen = set()
        
        for node in path:
            if node not in seen:
                cleaned.append(node)
                seen.add(node)
        
        if cleaned[0] != start:
            cleaned.insert(0, start)
        if cleaned[-1] != end:
            cleaned.append(end)
        
        return cleaned

    def _greedy_fallback(self, start, end):
        """Fallback to greedy algorithm."""
        current = start
        path = [current]
        visited = {current}
        
        while current != end and len(path) < len(self.nodes):
            neighbors = [
                (n, self.graph[current][n])
                for n in self.graph[current].keys()
                if n not in visited
            ]
            
            if not neighbors:
                return []
            
            next_node = min(neighbors, key=lambda x: x[1])[0]
            path.append(next_node)
            visited.add(next_node)
            current = next_node
        
        return path if current == end else []