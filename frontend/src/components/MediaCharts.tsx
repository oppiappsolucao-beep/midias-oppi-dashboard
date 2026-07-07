"use client";

import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const COLORS = ["#7C3AED", "#C026D3", "#6366F1", "#14B8A6", "#F59E0B", "#EF4444"];

interface ChartsProps {
  porEmpresa: { Empresa: string; Total: number }[];
  porStatus: { "Status Pagamento": string; Valor: number }[];
}

export function MediaCharts({ porEmpresa, porStatus }: ChartsProps) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="section-card">
        <h3 className="mb-4 text-base font-bold">📊 Publicações por empresa</h3>
        {porEmpresa.length === 0 ? (
          <p className="text-sm text-slate-500">Sem dados para esse filtro.</p>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={porEmpresa}>
              <XAxis dataKey="Empresa" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="Total" fill="#7C3AED" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="section-card">
        <h3 className="mb-4 text-base font-bold">💳 Valor por status pagamento</h3>
        {porStatus.length === 0 ? (
          <p className="text-sm text-slate-500">Sem valores para esse filtro.</p>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <PieChart>
              <Pie
                data={porStatus}
                dataKey="Valor"
                nameKey="Status Pagamento"
                innerRadius={70}
                outerRadius={110}
                paddingAngle={2}
              >
                {porStatus.map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => `R$ ${value.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`} />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
