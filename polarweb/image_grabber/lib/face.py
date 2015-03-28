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

    debug = False

    def __init__(self):
        self.evidence = {}
        self.face_id = 0

    def observe(self, faces):
        # Match faces up

        faces_now = list()
        for input_face in faces:
            radial = self.to_radial(input_face)
            face_id, dist = self.closest_face(radial)

            if face_id is not None and dist < self.tolerance:
                face = self.evidence[face_id]
                face['observations'].append(radial)
                face['rects'].append(input_face)
                faces_now.append(face_id)
                if self.debug:
                    print "got face id %s" % face_id

            else:
                self.face_id += 1
                face_id = self.face_id

                self.evidence[face_id] = {
                    'radial': radial,
                    'observations': [radial],
                    'rects': [input_face],
                    'score': self.score_initial,
                }

        # boost the biggest face
        if self.evidence is not None and len(self.evidence):
            biggest = self.faces_by_size()[0]
            face_id = biggest[0]
            if face_id in faces_now:
                self.evidence[face_id]['score'] += self.score_boost
                print "Boosted id %s to %s" % (face_id, self.evidence[face_id]['score'])

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
        l = list(sorted(
            self.evidence.iteritems(),
            lambda x, y: cmp(y[1]['radial'][2], x[1]['radial'][2])
        ))

        if self.debug:
            print [i[0] for i in l]

        return l

    def face_boundary(self, face_id):
        return self.moving_average(self.evidence[face_id]['rects'])

    def highlight_faces(self, frame, scale, all_faces=None, big_faces=None, debug=False):
        first = True
        white = (255, 255, 255)
        black = (50, 50, 50)
        msg = ["", ""]


        for key, evidence in self.faces_by_size():
            (x, y, r) = [int(i*scale) for i in evidence['radial']]

            score_r = r * float(evidence['score']) / float(self.score_max)
            cv2.circle(frame, (x, y), int(r),
                       (0, 255, 0), 3)
            cv2.circle(frame, (x, y), int(score_r),
                       (0, 255, 0), 3)

            y_offset = y + int(r) + 25
            cv2.putText(frame, "id: %s" % key, (x, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, white)
            y_offset += 16
            cv2.putText(frame, "size: %s" % r, (x, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, white)
            y_offset += 16
            cv2.putText(frame, "score: %s" % evidence['score'], (x, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, white)

            if debug:
                cv2.line(frame, (x, y), (int(x+r*0.7), int(y+r*0.7)),
                         (0, 255, 0), 1)

            if first:
                cv2.circle(frame, (x, y), int(r),
                           (255, 255, 255), 5)
                cv2.circle(frame, (x, y), int(r)+4,
                           (0, 0, 0), 2)

                score_percent = float(evidence['score']) / float(self.score_max) * 100.0
                msg = ["Locking... %d%%" % score_percent, ""]
                cv2.putText(frame, msg[0], (5, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, black, 6)
                cv2.putText(frame, msg[0], (5, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, white, 2)

                first = False

        if msg == ["", ""]:
            if all_faces is not None and \
               len(all_faces) and not big_faces:
                msg = ["Please come closer...", ""]
            elif all_faces is None or not len(all_faces):
                msg = ["Looking for", "people to draw.."]

        cv2.putText(frame, msg[0], (5, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, black, 6)
        cv2.putText(frame, msg[1], (5, 25+35),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, black, 6)

        cv2.putText(frame, msg[0], (5, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, white, 2)
        cv2.putText(frame, msg[1], (5, 25+35),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, white, 2)


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
        r = r * 0.7

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

    def scale_rect(self, rect, ratio):
        return [i*ratio for i in rect]
