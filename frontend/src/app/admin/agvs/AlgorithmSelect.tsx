import React from "react";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface AlgorithmSelectProps {
  selectedAlgorithm: string;
  onAlgorithmChange: (value: string) => void;
}

export function AlgorithmSelect({
  selectedAlgorithm,
  onAlgorithmChange,
}: AlgorithmSelectProps) {
  return (
    <Select
      value={selectedAlgorithm}
      onValueChange={onAlgorithmChange}
    >
      <SelectTrigger className="w-full">
        <SelectValue placeholder="Select Algorithm" />
      </SelectTrigger>
      <SelectContent className="z-50">
        <SelectGroup>
          <SelectLabel>Algorithms</SelectLabel>
          <SelectItem value="dijkstra">Dijkstra</SelectItem>
          <SelectItem value="greedy">Greedy Distance</SelectItem>
          <SelectItem value="hill_climbing">Hill Climbing</SelectItem>
          <SelectItem value="pso_ga">Hybrid PSO-GA</SelectItem>
        </SelectGroup>
      </SelectContent>
    </Select>
  );
}
