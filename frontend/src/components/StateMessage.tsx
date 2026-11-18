export default function StateMessage({ message }: { message: string }) {
  return <div className="state-message">{message}<small>Run preprocessing and training, then start the FastAPI server on port 8000.</small></div>;
}
