import numpy as np


def threshold(image, boundaries):
    oot = np.zeros(image.shape)

    for (i, boundary) in enumerate(boundaries):
        level = np.float64(float(i + 1) / len(boundaries))
        oot[image > boundary] = level

    # multiply and get back to good ole ints
    for each in oot:
        each *= 255

    return oot.astype(np.uint8)


def histogram(image):
    hist = [0] * 256

    for value in image[image >= 0]:
        hist[value] += 1

    return hist


def sub_image(image, rect):
    (x, y, w, h) = [int(i) for i in rect]

    return image[y:y + h, x:x + w]


def get_threshold_boundaries(image, count):
    hist = histogram(image)
    total = sum(hist)

    cumulative = 0
    pos = 1
    boundaries = []

    for (i, value) in enumerate(hist):
        cumulative += value
        if cumulative >= pos * total / (count + 1):
            boundaries.append(i)
            pos += 1

    return boundaries[:-1]