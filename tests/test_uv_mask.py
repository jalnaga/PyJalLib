# -*- coding: utf-8 -*-
"""uvMask 순수 모듈 테스트 (Type A) - 정답을 아는 도형으로 픽셀 수를 단정한다.

- 전면 사각형 = 전부 칠함 / 반면 삼각형 = 면적 비 ±1% / 빈 입력 = 바탕 그대로 / 클립 / 팽창 / 퇴화
- v 뒤집기: v가 큰 UV가 이미지 **위쪽**에 찍힌다
- TGA 왕복: 헤더 필드·크기·픽셀 등호. 24-bit(기록)과 32-bit·top-left(판독 호환)
"""

import struct

import pytest

from pyjallib.max import uvMask
from pyjallib.max.uvMask import MaskImage, bake_face_mask, dilate, read_tga, write_tga

SQUARE_VERTS = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
SQUARE_FACES = [[0, 1, 2, 3]]


def test_full_square_paints_every_pixel():
    image, stats = bake_face_mask(SQUARE_VERTS, SQUARE_FACES, [0], 64)
    assert image.count(0) == 64 * 64
    assert stats.faceCount == 1
    assert stats.zeroPixelFaces == 0
    assert stats.paintedPixels == 64 * 64


def test_half_triangle_covers_half_area():
    verts = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]
    image, _ = bake_face_mask(verts, [[0, 1, 2]], [0], 256)
    ratio = image.count(0) / (256 * 256)
    assert abs(ratio - 0.5) < 0.01


def test_empty_face_list_keeps_fill():
    image, stats = bake_face_mask(SQUARE_VERTS, SQUARE_FACES, [], 32)
    assert image.count(255) == 32 * 32
    assert stats.faceCount == 0
    assert stats.paintedPixels == 0


def test_custom_fill_and_value():
    image, _ = bake_face_mask(SQUARE_VERTS, SQUARE_FACES, [0], 8, inFill=0, inValue=255)
    assert image.count(255) == 64


def test_uv_outside_unit_square_is_clipped():
    verts = [(-1.0, -1.0), (2.0, -1.0), (2.0, 2.0), (-1.0, 2.0)]
    image, stats = bake_face_mask(verts, [[0, 1, 2, 3]], [0], 16)
    assert image.count(0) == 16 * 16
    # 완전히 밖인 면은 아무것도 칠하지 않고 0픽셀 면으로 센다
    outside = [(2.0, 2.0), (3.0, 2.0), (3.0, 3.0)]
    image2, stats2 = bake_face_mask(outside, [[0, 1, 2]], [0], 16)
    assert image2.count(0) == 0
    assert stats2.zeroPixelFaces == 1


def test_v_axis_is_flipped_top_is_high_v():
    # v 0.75..1.0 띠 -> 이미지 위쪽 1/4
    verts = [(0.0, 0.75), (1.0, 0.75), (1.0, 1.0), (0.0, 1.0)]
    image, _ = bake_face_mask(verts, [[0, 1, 2, 3]], [0], 16)
    for y in range(4):
        assert all(image.get(x, y) == 0 for x in range(16))
    for y in range(4, 16):
        assert all(image.get(x, y) == 255 for x in range(16))


def test_small_face_without_pixel_center_counts_zero():
    # 0.1픽셀짜리 삼각형: 중심을 덮지 못한다
    verts = [(0.30, 0.30), (0.31, 0.30), (0.30, 0.31)]
    image, stats = bake_face_mask(verts, [[0, 1, 2]], [0], 16)
    assert stats.zeroPixelFaces == 1
    assert stats.perFacePixels == [0]
    assert image.count(0) == 0


def test_degenerate_triangle_is_ignored():
    verts = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0)]
    image, stats = bake_face_mask(verts, [[0, 1, 2]], [0], 16)
    assert image.count(0) == 0
    assert stats.zeroPixelFaces == 1


def test_fan_triangulation_of_quad_equals_two_triangles():
    quad = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    tris = uvMask.triangulate_fan(quad)
    assert tris == [((0.0, 0.0), (10.0, 0.0), (10.0, 10.0)), ((0.0, 0.0), (10.0, 10.0), (0.0, 10.0))]
    assert uvMask.triangulate_fan(quad[:2]) == []


def test_winding_does_not_matter():
    cw = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)]
    image, _ = bake_face_mask(cw, [[0, 1, 2, 3]], [0], 8)
    assert image.count(0) == 64


def test_dilate_zero_is_identity_and_one_grows_border():
    image = MaskImage(9, 9)
    image.set(4, 4, 0)
    same = dilate(image, 0)
    assert same == image
    assert same is not image
    grown = dilate(image, 1)
    assert grown.count(0) == 9
    assert image.count(0) == 1  # 원본 불변
    grown2 = dilate(image, 2)
    assert grown2.count(0) == 25


def test_dilate_through_bake_padding():
    verts = [(0.5, 0.5), (0.5625, 0.5), (0.5625, 0.5625), (0.5, 0.5625)]  # 16x16에서 1픽셀
    image, stats = bake_face_mask(verts, [[0, 1, 2, 3]], [0], 16, inPadding=1)
    assert stats.perFacePixels == [1]
    assert stats.paintedPixels == 9
    assert image.count(0) == 9


def test_invalid_arguments_raise():
    with pytest.raises(ValueError):
        MaskImage(0, 4)
    with pytest.raises(ValueError):
        bake_face_mask(SQUARE_VERTS, SQUARE_FACES, [1], 8)
    with pytest.raises(ValueError):
        dilate(MaskImage(2, 2), -1)
    with pytest.raises(ValueError):
        bake_face_mask(SQUARE_VERTS, SQUARE_FACES, [0], 8, inValue=300)


def test_tga_round_trip_24bit_bottom_left(tmp_path):
    verts = [(0.0, 0.5), (1.0, 0.5), (1.0, 1.0), (0.0, 1.0)]
    image, _ = bake_face_mask(verts, [[0, 1, 2, 3]], [0], 8)
    path = str(tmp_path / "sub" / "mask.tga")
    write_tga(path, image)
    info = uvMask.tga_header_info(path)
    assert info == {
        "idLength": 0,
        "colorMapType": 0,
        "imageType": 2,
        "width": 8,
        "height": 8,
        "depth": 24,
        "descriptor": 0,
    }
    assert (tmp_path / "sub" / "mask.tga").stat().st_size == 18 + 8 * 8 * 3
    back = read_tga(path)
    assert back == image
    # 위 절반이 검정(v 0.5..1), 아래 절반이 흰색
    assert back.get(0, 0) == 0 and back.get(7, 3) == 0
    assert back.get(0, 4) == 255 and back.get(7, 7) == 255


def test_read_tga_accepts_32bit_top_left(tmp_path):
    width, height = 4, 2
    header = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, width, height, 32, 0x28)
    rows = []
    for y in range(height):
        for x in range(width):
            value = 0 if y == 0 else 255
            rows.append(bytes((value, value, value, 255)))
    path = tmp_path / "tl.tga"
    path.write_bytes(header + b"".join(rows))
    image = read_tga(str(path))
    assert image.width == width and image.height == height
    assert [image.get(x, 0) for x in range(width)] == [0] * width
    assert [image.get(x, 1) for x in range(width)] == [255] * width


def test_read_tga_rejects_other_formats(tmp_path):
    path = tmp_path / "bad.tga"
    path.write_bytes(struct.pack("<BBBHHBHHHHBB", 0, 1, 1, 0, 0, 0, 0, 0, 2, 2, 8, 0) + b"\0" * 4)
    with pytest.raises(ValueError):
        read_tga(str(path))
    path.write_bytes(b"\0" * 5)
    with pytest.raises(ValueError):
        read_tga(str(path))
