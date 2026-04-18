"use client";

import {
  Radar,
  RadarChart as RechartsRadar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";

interface Props {
  scores: Record<string, number>;
  labels: Record<string, string>;
}

export default function RadarChart({ scores, labels }: Props) {
  const data = Object.entries(scores).map(([key, value]) => ({
    dimension: labels[key] ?? key,
    score: value,
    fullMark: 5,
  }));

  return (
    <div className="mx-auto h-72 w-72 sm:h-80 sm:w-80">
      <ResponsiveContainer width="100%" height="100%">
        <RechartsRadar cx="50%" cy="50%" outerRadius="75%" data={data}>
          <PolarGrid stroke="#E7E5E0" />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{ fontSize: 11, fill: "#78716C", fontFamily: '"Plus Jakarta Sans", sans-serif' }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 5]}
            tick={{ fontSize: 10, fill: "#A8A29E" }}
            tickCount={6}
          />
          <Radar
            name="Score"
            dataKey="score"
            stroke="#C2410C"
            fill="#FED7AA"
            fillOpacity={0.25}
            strokeWidth={2}
          />
        </RechartsRadar>
      </ResponsiveContainer>
    </div>
  );
}
