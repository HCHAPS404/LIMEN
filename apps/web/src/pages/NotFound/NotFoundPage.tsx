import { Link, useLocation } from "react-router-dom";

import { EmptyState } from "../../components/feedback/EmptyState";
import { GlassPanel } from "../../components/glass/Panel";
import { Button } from "../../components/primitives/Button";
import { WorkspaceSplit } from "../../components/shell/AppShell";

export function NotFoundPage() {
  const { pathname } = useLocation();

  return (
    <WorkspaceSplit>
      <GlassPanel className="min-h-0 flex-1">
        <EmptyState
          eyebrow="Nowhere"
          title="This surface does not exist"
          description={`There is no route at ${pathname}. Use the navigation rail to reach the call, knowledge, trace, session, or settings surfaces.`}
          action={
            <Button variant="primary" asChild>
              <Link to="/call">Go to call</Link>
            </Button>
          }
        />
      </GlassPanel>
    </WorkspaceSplit>
  );
}
