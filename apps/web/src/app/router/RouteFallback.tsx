import { LoadingState } from "../../components/feedback/LoadingState";

/** Shown while a lazily-loaded surface is fetched. */
export function RouteFallback() {
  return (
    <div className="p-5">
      <LoadingState label="Loading surface" rows={3} />
    </div>
  );
}
