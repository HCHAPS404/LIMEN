export function CallPage() {
  return (
    <section className="panel" aria-labelledby="call-title">
      <h1 id="call-title">Llamada</h1>
      <p>
        Interfaz de voz en tiempo real (micrófono → STT → agente → TTS). Estado:{" "}
        <strong>Planned</strong> — el shell de navegación ya está listo.
      </p>
    </section>
  );
}
