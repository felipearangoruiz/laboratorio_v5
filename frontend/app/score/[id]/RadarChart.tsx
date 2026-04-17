"use client";

import {
  Radar,
  RadarChart as RechartsRadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";
import type { DimensionScore } from "@/lib/types";

interface Props {
  dimensions: DimensionScore[];
}

export default function RadarChart({ dimensions }: Props) {
  const data = dimensions.map((d) => ({
    dimension: d.label,
    score: d.score,
    fullMark: d.max_score,
  }));

  return (
    <div className="w-full h-72">
      <ResponsiveContainer width="100%" height="100%">
        <RechartsRadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
          <PolarGrid stroke="#e5e7eb" />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{ fill: "#374151", fontSize: 12 }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 5]}
            tick={{ fill: "#9ca3af", fontSize: 10 }}
          />
          <Radar
            name="Score"
            dataKey="score"
            stroke="#111827"
            fill="#111827"
            fillOpacity={0.15}
            strokeWidth={2}
          />
        </RechartsRadarChart>
      </ResponsiveContainer>
    </div>
  );
}
