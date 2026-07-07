"use client";

import { useCallback, useEffect, useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { MediaCharts } from "@/components/MediaCharts";
import { MediaRowCard } from "@/components/MediaRowCard";
import { MetricCard } from "@/components/MetricCard";
import { fetchMediaDashboard, type MediaDashboard } from "@/lib/api";
import { useAuthGuard } from "@/lib/useAuthGuard";

export default function MidiasPage() {
  const ready = useAuthGuard();
  const [data, setData] = useState<MediaDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [mes, setMes] = useState("Todos");
  const [semana, setSemana] = useState("Todas");
  const [empresa, setEmpresa] = useState("Todas");
  const [datas, setDatas] = useState<string[]>([]);
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await fetchMediaDashboard({ mes, semana, empresa, datas, busca: buscaAplicada });
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar dados.");
    } finally {
      setLoading(false);
    }
  }, [mes, semana, empresa, datas, buscaAplicada]);

  useEffect(() => {
    const timer = setTimeout(() => setBuscaAplicada(busca), 400);
    return () => clearTimeout(timer);
  }, [busca]);

  useEffect(() => {
    if (ready) loadData();
  }, [ready, loadData]);

  if (!ready) return null;

  return (
    <DashboardLayout
      title="📱 Gestão de publicações e pagamentos"
      subtitle="Gestão de publicações e pagamentos"
    >
      <div className="filter-card mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div>
          <label className="mb-1 block text-sm font-medium">Mês</label>
          <select className="select-field" value={mes} onChange={(e) => setMes(e.target.value)}>
            <option value="Todos">Todos</option>
            {data?.filters.meses.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Semana</label>
          <select className="select-field" value={semana} onChange={(e) => setSemana(e.target.value)}>
            <option value="Todas">Todas</option>
            {data?.filters.semanas.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Empresa</label>
          <select className="select-field" value={empresa} onChange={(e) => setEmpresa(e.target.value)}>
            <option value="Todas">Todas</option>
            {data?.filters.empresas.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Datas publicação</label>
          <select
            className="select-field"
            multiple
            value={datas}
            onChange={(e) =>
              setDatas(Array.from(e.target.selectedOptions, (option) => option.value))
            }
          >
            {data?.filters.datas.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
          <p className="mt-1 text-xs text-slate-400">Segure Ctrl para selecionar várias datas.</p>
        </div>
      </div>

      {loading && <p className="text-sm text-slate-500">Carregando...</p>}
      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {data && (
        <>
          <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
            <MetricCard title="Posts" value={data.metrics.total_posts} subtitle="total de registros filtrados" />
            <MetricCard title="Valor total" value={data.metrics.total_valor_fmt} subtitle="soma de todas as mídias" />
            <MetricCard title="Pagos" value={data.metrics.pagos_count} subtitle="status pagamento = Pago" />
            <MetricCard title="A pagar" value={data.metrics.a_pagar_count} subtitle="status pagamento = A pagar" />
            <MetricCard title="Valor pago" value={data.metrics.valor_pago_fmt} subtitle="somatório dos pagos" />
            <MetricCard title="Valor pendente" value={data.metrics.valor_pendente_fmt} subtitle="somatório em aberto" />
          </div>

          <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="Postagens feitas" value={data.metrics.postagens_feitas} subtitle="status da arte = Pronto" variant="metric-card-green" />
            <MetricCard title="Postagens a fazer" value={data.metrics.postagens_a_fazer} subtitle="status diferente de Pronto" variant="metric-card-orange" />
            <MetricCard title="Em andamento" value={data.metrics.em_andamento} subtitle="status da arte = Em andamento" variant="metric-card-orange" />
            <MetricCard title="Concluído" value={data.metrics.concluido} subtitle="status da arte = Concluído" variant="metric-card-blue" />
          </div>

          <div className="mb-6">
            <MediaCharts
              porEmpresa={data.charts.por_empresa}
              porStatus={data.charts.por_status_pagamento}
            />
          </div>

          <div className="table-card space-y-4">
            <div>
              <h3 className="text-base font-bold">✏️ Atualizar status da arte</h3>
              <p className="text-sm text-slate-500">
                Atualize a coluna &quot;Status da arte&quot; diretamente pela interface abaixo.
              </p>
            </div>
            <input
              className="input-field"
              placeholder="Buscar por empresa ou tema"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
            />
            <div className="space-y-3">
              {data.rows.length === 0 ? (
                <p className="text-sm text-slate-500">Nenhum registro encontrado com esse filtro.</p>
              ) : (
                data.rows.map((row) => (
                  <MediaRowCard key={row.row_index} row={row} onUpdated={loadData} />
                ))
              )}
            </div>
          </div>
        </>
      )}
    </DashboardLayout>
  );
}
