type Data = Record<string, any>;
const measured = (v: unknown) =>
  typeof v === "number" && Number.isFinite(v) ? v.toFixed(4) : "Not recorded";
export default function SegmentationEvidence({
  manifest: m,
}: {
  manifest: Data | undefined;
}) {
  if (!m?.model_name?.startsWith("tiny_unet")) return null;
  return (
    <section aria-label="Learned segmentation evidence">
      <h3>Actual learned segmentation evaluation</h3>
      <p>
        {m.model_name} · {m.input_size}px square representation ·
        validation-selected threshold {m.threshold}.
      </p>
      <p className="notice">{m.limitation}</p>
      <p>
        Image split: training {m.split_image_ids.train.length}, validation{" "}
        {m.split_image_ids.validation.length}, test{" "}
        {m.split_image_ids.test.length}. Threshold and checkpoint chosen on
        validation Dice only.
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Method on the same held-out images</th>
              <th>Mean Dice</th>
              <th>Mean IoU</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{m.model_name}</td>
              <td>{measured(m.test_metrics?.mean_dice)}</td>
              <td>{measured(m.test_metrics?.mean_iou)}</td>
            </tr>
            {Object.entries(
              m.classical_baselines_same_test_representation || {},
            ).map(([name, value]) => {
              const metric = value as Data;
              return (
                <tr key={name}>
                  <td>{name}</td>
                  <td>{measured(metric.mean_dice)}</td>
                  <td>{measured(metric.mean_iou)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p>
        These measurements describe a small research cohort, not clinical
        localization accuracy or native-resolution boundary reliability.
      </p>
    </section>
  );
}
