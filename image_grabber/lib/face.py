import math
import cv2


class Tracking(object):
    watcher = {}
    max_observations = 5
    tolerance = 1500

    score_initial = 2
    score_decay = -1
    score_boost = 2
    score_max = 50

    def __init__(self):
        self.evidence = {}
        self.face_id = 0

    def observe(self, faces):
        # Match faces up
        new_faces = {}
        for input_face in faces:
            radial = self.to_radial(input_face)
            face_id, dist = self.closest_face(radial)

            if face_id is not None and dist < self.tolerance:
                face = self.evidence[face_id]
                face['observations'].append(radial)
                face['rects'].append(input_face)
                face['score'] += self.score_boost

            else:
                self.face_id += 1
                face_id = self.face_id

                self.evidence[face_id] = {
                    'radial': radial,
                    'observations': [radial],
                    'rects': [input_face],
                    'score': self.score_initial,
                }

        # Update faces
        for face_id in self.evidence.keys():
            face = self.evidence[face_id]
            face['score'] += self.score_decay

            if face['score'] < 0:
                self.evidence.pop(face_id)
                continue

            if face['score'] > self.score_max:
                face['score'] = self.score_max

            # Trim to the last X pieces of evidence
            if len(face['observations']) > self.max_observations:
                face['observations'] = \
                    face['observations'][-self.max_observations:]
                face['rects'] = \
                    face['rects'][-self.max_observations:]

            # Update our radial position based on a weighted average of
            # the values we have seen:
            if len(face['observations']) > 1:
                face['radial'] = self.moving_average(face['observations'])

    def moving_average(self, items):
        average = [0.0 for _ in items[0]]
        mult = 1
        mult_cumulative = 0

        for item in items:
            for i in range(len(item)):
                average[i] += mult * item[i]
            mult_cumulative += mult
            mult += 1

        return [i/mult_cumulative for i in average]

    def to_radial(self, face_dims):
        (x, y, w, h) = face_dims
        radius = math.sqrt( math.pow(w/2, 2) + math.pow(h/2, 2))

        return x+w/2, y+h/2, radius

    def closest_face(self, radial):
        min_dist = None
        min_face_id = None

        for (face_id, face) in self.evidence.iteritems():
            dist = sum([
                math.pow(a - b,2) for (a, b) in zip(face['radial'], radial)])

            if min_dist is None or dist < min_dist:
                min_dist = dist
                min_face_id = face_id

        return min_face_id, min_dist

    def faces_by_size(self):
        return sorted(
            self.evidence.iteritems(),
            lambda x, y: cmp(x[1]['radial'][2], y[1]['radial'][2])
        )

    def face_boundary(self, face_id):
        return self.moving_average(self.evidence[face_id]['rects'])

    def highlight_faces(self, frame, scale):
        for evidence in self.evidence.values():
            (x, y, r) = [int(i*scale) for i in evidence['radial']]

            score_r = r * float(evidence['score']) / float(self.score_max)
            cv2.circle(frame, (x, y), int(r),
                       (0, 255, 0), 2)
            cv2.circle(frame, (x, y), int(score_r),
                       (0, 255, 0), 1)
            cv2.line(frame, (x, y), (int(x+r*0.7), int(y+r*0.7)),
                     (0, 255, 0), 1)


class Framing(object):
    def __init__(self, frame):
        self.frame = frame
        self.width = len(frame[0])
        self.height = len(frame)

    def get_border(self, rect):
        (x, y, w, h) = rect

        return y, self.width - x - w, x, self.height - y - h

    def single_portrait(self, rect):
        (x, y, w, h) = rect
        r = min([(w + h) / 4, self.width / 4])

        (cx, cy) = (x + w / 2, y + h / 2)

        right = self.width - cx
        bottom = self.height - cy

        portrait_ratio = ((4 * math.pow(2, 0.5)) - 2.5)

        r = min(cx / 2, cy / 2.5, right / 2, bottom / portrait_ratio, r)

        return (
            int(cx - 2 * r),
            int(cy - 2.5 * r),
            4 * r,
            4 * math.pow(2, 0.5) * r
        )

    def tighten_rect(self, rect, ratio):
        (x, y, w, h) = rect

        dx = (1.0 - ratio) * float(w) / 2
        dy = (1.0 - ratio) * float(h) / 2

        return x + dx, y + dy, w - 2 * dx, h - 2 * dy