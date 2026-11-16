import PixelFlowField from "@/components/PixelFlowField";

const releaseUrl = "https://github.com/roshandhiman/ai_linux-DIST/releases/latest";

export default function Home() {
  return (
    <main className="landing">
      <PixelFlowField
        text="MineOS"
        className="landing-field"
        colors={["#e2d5db", "#d3619d", "#e4c9d7"]}
        cellSize={8}
        gap={3}
        speed={0.7}
        weight={800}
        pointerRadius={110}
        pointerStrength={0.72}
      >
        <h1 className="landing-wordmark">MineOS</h1>
        <div className="landing-copy">
          <p>AI-powered operating system</p>
          <a className="download" href={releaseUrl}>Download</a>
        </div>
      </PixelFlowField>
    </main>
  );
}
