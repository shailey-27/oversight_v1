"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { LiveKitRoom, VideoConference, RoomAudioRenderer, ControlBar } from "@livekit/components-react";
import "@livekit/components-styles";
import api from "@/lib/api";

export default function VideoCallPage() {
  const params = useParams();
  const callId = params.id;
  const [token, setToken] = useState("");

  useEffect(() => {
    async function getToken() {
      try {
        // Fetch a secure LiveKit token from our FastAPI backend
        const res = await api.get(`/livekit/token?room=${callId}`);
        setToken(res.data.token);
      } catch (error) {
        console.error("Failed to get LiveKit token", error);
      }
    }
    
    if (callId) {
      getToken();
    }
  }, [callId]);

  if (!token) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column' }}>
        <h2>Connecting to Secure Government Room...</h2>
        <p style={{ color: 'var(--text-muted)' }}>Generating encrypted LiveKit tokens...</p>
      </div>
    );
  }

  return (
    <div style={{ height: "100vh", width: "100%" }}>
      <LiveKitRoom
        video={true}
        audio={true}
        token={token}
        serverUrl={process.env.NEXT_PUBLIC_LIVEKIT_URL}
        data-lk-theme="default"
        style={{ height: "100%" }}
      >
        <VideoConference />
        <RoomAudioRenderer />
        <ControlBar />
      </LiveKitRoom>
    </div>
  );
}
