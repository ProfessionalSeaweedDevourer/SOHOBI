import { useEffect } from "react";
import MapView from "../components/map/MapView";
import { trackEvent } from "../utils/trackEvent";

export default function MapPage() {
  useEffect(() => {
    trackEvent("feature_discovery", { page: "map" });
  }, []);

  return <MapView />;
}
