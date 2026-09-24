'use client';

import { useEffect } from 'react';
import { RoomEvent, RemoteParticipant } from 'livekit-client';
import { useRoomContext } from '@livekit/components-react';
import { toast } from 'sonner';

export function useDataChannelCommands() {
  let room;
  try {
    room = useRoomContext();
  } catch (e) {
    room = null;
  }

  useEffect(() => {
    if (!room) return;

    const handleDataReceived = (
      payload: Uint8Array,
      participant?: RemoteParticipant
    ) => {
      try {
        const text = new TextDecoder().decode(payload);
        console.log('[Jarvis DataChannel] Raw data received:', text);
        const data = JSON.parse(text);

        if (data.type === 'open_url' && data.url) {
          console.log('[Jarvis DataChannel] Received open_url:', data.url);

          // Attempt to open in a new tab directly in user's active browser
          try {
            window.open(data.url, '_blank');
          } catch (e) {
            console.error('[Jarvis DataChannel] window.open failed:', e);
          }

          // Also show clean toast notification with direct link in case popups are blocked by browser settings
          toast.info(`Jarvis target opened: ${data.url}`, {
            action: {
              label: 'Open Webpage',
              onClick: () => window.open(data.url, '_blank'),
            },
            duration: 10000,
          });
        }
      } catch (err) {
        // Ignore non-matching data channel packets
      }
    };

    room.on(RoomEvent.DataReceived, handleDataReceived);

    return () => {
      room.off(RoomEvent.DataReceived, handleDataReceived);
    };
  }, [room]);
}
