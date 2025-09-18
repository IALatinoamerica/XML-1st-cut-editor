import type { SilenceSettings } from '../types';

export const processXml = (xmlString: string, settings: SilenceSettings): string => {
  const parser = new DOMParser();
  const xmlDoc = parser.parseFromString(xmlString, "application/xml");
  const parseError = xmlDoc.querySelector("parsererror");
  if (parseError) {
    throw new Error("Failed to parse XML file. Please ensure it's a valid Premiere Pro XML.");
  }

  const sequence = xmlDoc.querySelector("sequence");
  if (!sequence) {
    throw new Error("Could not find a <sequence> in the XML file.");
  }

  const timebaseEl = sequence.querySelector("timebase");
  const timebase = timebaseEl ? parseInt(timebaseEl.textContent || '30', 10) : 30;

  const thresholdTicks = Math.round(settings.silenceThreshold * timebase);
  const paddingTicks = Math.round(settings.clipPadding * timebase);

  const videoTrack = sequence.querySelector("video > track");
  if (!videoTrack) {
    throw new Error("Could not find a video track in the sequence.");
  }

  const originalClips = Array.from(videoTrack.querySelectorAll("clipitem"));
  if (originalClips.length === 0) {
      throw new Error("No clips found on the main video track.");
  }
  
  const newClips: Element[] = [];
  let timelineCursor = 0;

  originalClips.forEach((clip, index) => {
    const startEl = clip.querySelector("start");
    const endEl = clip.querySelector("end");
    const inEl = clip.querySelector("in");
    const outEl = clip.querySelector("out");

    if (!startEl || !endEl || !inEl || !outEl) return;

    const originalStart = parseInt(startEl.textContent || '0', 10);
    const originalEnd = parseInt(endEl.textContent || '0', 10);
    const originalIn = parseInt(inEl.textContent || '0', 10);

    const duration = originalEnd - originalStart;

    // We simulate a "cut" in the middle of any clip long enough to be split
    const minDurationForCut = thresholdTicks + (paddingTicks * 2);

    if (duration > minDurationForCut) {
      const remainingDuration = duration - thresholdTicks;
      const firstPartDuration = Math.round(remainingDuration / 2);
      const secondPartDuration = remainingDuration - firstPartDuration;

      // Create first part of the clip
      const clip1 = clip.cloneNode(true) as Element;
      clip1.setAttribute('id', `${clip.getAttribute('id')}-part1`);
      
      const c1Start = clip1.querySelector('start');
      const c1End = clip1.querySelector('end');
      const c1In = clip1.querySelector('in');
      const c1Out = clip1.querySelector('out');
      
      if(c1Start && c1End && c1In && c1Out) {
        c1Start.textContent = String(timelineCursor);
        c1End.textContent = String(timelineCursor + firstPartDuration);
        c1In.textContent = String(originalIn);
        c1Out.textContent = String(originalIn + firstPartDuration);
        newClips.push(clip1);
        timelineCursor += firstPartDuration;
      }
      
      // Create second part of the clip
      const clip2 = clip.cloneNode(true) as Element;
      clip2.setAttribute('id', `${clip.getAttribute('id')}-part2`);
      
      const c2Start = clip2.querySelector('start');
      const c2End = clip2.querySelector('end');
      const c2In = clip2.querySelector('in');
      const c2Out = clip2.querySelector('out');

      if(c2Start && c2End && c2In && c2Out) {
        const secondPartInPoint = originalIn + firstPartDuration + thresholdTicks;
        c2Start.textContent = String(timelineCursor);
        c2End.textContent = String(timelineCursor + secondPartDuration);
        c2In.textContent = String(secondPartInPoint);
        c2Out.textContent = String(secondPartInPoint + secondPartDuration);
        newClips.push(clip2);
        timelineCursor += secondPartDuration;
      }
    } else {
      // If clip is too short to cut, just place it on the new timeline
      const newClip = clip.cloneNode(true) as Element;
      const ncStart = newClip.querySelector('start');
      const ncEnd = newClip.querySelector('end');
      if(ncStart && ncEnd) {
        ncStart.textContent = String(timelineCursor);
        ncEnd.textContent = String(timelineCursor + duration);
        newClips.push(newClip);
        timelineCursor += duration;
      }
    }
  });

  // Replace old clips with new clips
  videoTrack.innerHTML = '';
  newClips.forEach(clip => videoTrack.appendChild(clip));
  
  // Update sequence duration
  const durationEl = sequence.querySelector("duration");
  if (durationEl) {
      durationEl.textContent = String(timelineCursor);
  }

  const serializer = new XMLSerializer();
  return serializer.serializeToString(xmlDoc);
};
