import { api } from "@/lib/api";
import { Brain, CheckCircle, XCircle } from "lucide-react";

const metricLabels: Record<string, string> = {
  accuracy: "Accuracy",
  f1: "F1 Score",
  log_loss: "Log Loss",
  precision: "Precision",
  recall: "Recall",
  auc: "AUC",
};

export default async function ModelsPage() {
  let models: Awaited<ReturnType<typeof api.getModels>> = [];

  try {
    models = await api.getModels();
  } catch {
    // API not available
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900">Model Registry</h1>
        <p className="text-zinc-500 mt-1">
          Trained ML models and their performance metrics
        </p>
      </div>

      {models.length > 0 ? (
        <div className="grid grid-cols-1 gap-4">
          {models.map((model) => (
            <div
              key={model.id}
              className="bg-white rounded-xl border border-zinc-200 p-5"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-lg bg-violet-500/10 text-violet-500">
                    <Brain size={20} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-semibold text-zinc-900">
                        {model.model_name}
                      </h3>
                      {model.is_active ? (
                        <span className="flex items-center gap-1 text-xs font-medium text-emerald-600 bg-emerald-100 px-2 py-0.5 rounded-full">
                          <CheckCircle size={10} />
                          Active
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-xs font-medium text-zinc-500 bg-zinc-100 px-2 py-0.5 rounded-full">
                          <XCircle size={10} />
                          Inactive
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-zinc-400 mt-0.5">
                      {model.model_type} &middot; v{model.model_version}
                    </p>
                  </div>
                </div>
                <span className="text-xs text-zinc-400">
                  {new Date(model.training_date).toLocaleDateString("sv-SE")}
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                {model.metrics
                  .filter((m) => m.dataset_type === "test")
                  .map((metric) => (
                    <div
                      key={metric.id}
                      className="bg-zinc-50 rounded-lg p-3 text-center"
                    >
                      <p className="text-xs text-zinc-400 mb-1">
                        {metricLabels[metric.metric_name] ?? metric.metric_name}
                      </p>
                      <p className="text-lg font-bold text-zinc-900">
                        {metric.metric_name === "log_loss"
                          ? metric.metric_value.toFixed(4)
                          : (metric.metric_value * 100).toFixed(1)}
                        <span className="text-xs font-normal text-zinc-400 ml-0.5">
                          {metric.metric_name === "log_loss" ? "" : "%"}
                        </span>
                      </p>
                    </div>
                  ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-16">
          <Brain size={48} className="mx-auto text-zinc-300 mb-4" />
          <p className="text-zinc-400">
            No models registered yet. Run the training pipeline.
          </p>
          <p className="text-xs text-zinc-300 mt-2">
            Use: <code className="bg-zinc-100 px-2 py-0.5 rounded">betting-bot train</code>
          </p>
        </div>
      )}
    </div>
  );
}
