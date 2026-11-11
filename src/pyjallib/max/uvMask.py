#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""UV 마스크 순수 모듈 - 면 집합을 UV 공간에 래스터화해 흑백 마스크 이미지로 만들고 TGA로 기록한다.

**pymxs·numpy·PIL을 import하지 않는다(stdlib만).** 추가 패키지를 설치할 수 없는 DCC 내장 Python에서
실행되고, 래스터화 규칙을 콘솔(Type A)에서 정답을 아는 도형으로 고정하기 위해서다. 씬에서 맵 버텍스·맵 면을
읽는 어댑터는 ``pyjallib.max.polygon.Polygon``(``read_map_faces`` / ``bake_face_mask``)이다.

## 좌표 규약

- 맵 버텍스는 ``(u, v)`` 튜플, 맵 면은 맵 버텍스 인덱스 목록(**0-based**, 폴리곤 순서). 1-based 변환은 어댑터
  경계에서 한다.
- 픽셀 좌표: ``x = u * width``, ``y = (1 - v) * height``. 3ds Max의 v 원점은 **아래**, 이미지 행 0은 **위**다.
- 0..1 밖 UV는 이미지 경계로 **클립**한다(랩하지 않는다).

## 픽셀 판정

픽셀 **중심**이 삼각형 안(경계 포함)이면 칠한다. 픽셀 중심을 하나도 덮지 못하는 작은 면은 칠해지지 않는다 -
오차는 "덜 칠함" 쪽으로만 기운다. 폴리곤은 UV 공간에서 팬(fan) 삼각분할한다. 공유 엣지에서 두 삼각형이 같은
픽셀을 칠하는 것은 무해하다(값이 같다).

## 값

바탕(``inFill``)과 칠(``inValue``)은 호출자가 정한다. 기본은 바탕 255(흰색), 칠 0(검정) - "흰색 = 남김,
검정 = 가려짐" 마스크다.

## TGA

비압축 24-bit RGB(R=G=B), 헤더 18바이트, **원점 좌하단(descriptor 0)** - 행을 아래부터 쓴다. 가장 널리 읽히는
형태다. ``read_tga``는 24/32-bit 비압축을 descriptor의 상하 플래그(bit 5)와 함께 읽는다(테스트·검증용).
"""

import os
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

Uv = Tuple[float, float]
Point = Tuple[float, float]
Triangle = Tuple[Point, Point, Point]

DEFAULT_FILL = 255
DEFAULT_VALUE = 0

TGA_HEADER_SIZE = 18
TGA_TYPE_TRUECOLOR = 2
TGA_DESCRIPTOR_TOP_LEFT = 0x20


class MaskImage:
    """1채널 8-bit 이미지(행 우선 ``bytearray``).

    Attributes:
        width: 가로 픽셀 수
        height: 세로 픽셀 수
        pixels: 행 우선 픽셀값(길이 width * height)
    """

    def __init__(self, inWidth: int, inHeight: int, inFill: int = DEFAULT_FILL) -> None:
        """이미지를 만든다.

        Args:
            inWidth: 가로 픽셀 수(1 이상)
            inHeight: 세로 픽셀 수(1 이상)
            inFill: 바탕값(0~255)

        Raises:
            ValueError: 크기가 1 미만이거나 값이 0~255 밖
        """
        if inWidth < 1 or inHeight < 1:
            raise ValueError(f"이미지 크기는 1 이상이어야 한다: {inWidth}x{inHeight}")
        _check_value(inFill)
        self.width = int(inWidth)
        self.height = int(inHeight)
        self.pixels = bytearray([inFill]) * (self.width * self.height)

    def get(self, inX: int, inY: int) -> int:
        """픽셀값(x, y)."""
        return self.pixels[inY * self.width + inX]

    def set(self, inX: int, inY: int, inValue: int) -> None:
        """픽셀값을 쓴다."""
        self.pixels[inY * self.width + inX] = inValue

    def count(self, inValue: int) -> int:
        """값이 inValue인 픽셀 수."""
        return self.pixels.count(inValue)

    def copy(self) -> "MaskImage":
        """사본."""
        out = MaskImage(self.width, self.height)
        out.pixels = bytearray(self.pixels)
        return out

    def __eq__(self, inOther: object) -> bool:
        return (
            isinstance(inOther, MaskImage)
            and self.width == inOther.width
            and self.height == inOther.height
            and self.pixels == inOther.pixels
        )


def _check_value(inValue: int) -> None:
    if not 0 <= int(inValue) <= 255:
        raise ValueError(f"픽셀값은 0~255여야 한다: {inValue}")


def uv_to_pixel(inUv: Uv, inWidth: int, inHeight: int) -> Point:
    """UV를 픽셀 좌표(연속값)로 바꾼다. v는 뒤집는다."""
    return (inUv[0] * inWidth, (1.0 - inUv[1]) * inHeight)


def triangulate_fan(inPoints: Sequence[Point]) -> List[Triangle]:
    """폴리곤 점 목록을 첫 점 기준 팬으로 삼각분할한다.

    Args:
        inPoints: 폴리곤 순서의 점(3개 이상. 2개 이하면 빈 목록)

    Returns:
        삼각형 목록
    """
    if len(inPoints) < 3:
        return []
    return [(inPoints[0], inPoints[i], inPoints[i + 1]) for i in range(1, len(inPoints) - 1)]


def triangle_pixel_indices(inTriangle: Triangle, inWidth: int, inHeight: int) -> List[int]:
    """픽셀 중심이 삼각형 안(경계 포함)인 픽셀의 행 우선 인덱스 목록.

    Args:
        inTriangle: 픽셀 좌표 삼각형
        inWidth: 이미지 가로
        inHeight: 이미지 세로

    Returns:
        인덱스 목록(이미지 경계로 클립, 퇴화 삼각형은 빈 목록)
    """
    (ax, ay), (bx, by), (cx, cy) = inTriangle
    area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    if area == 0.0:
        return []
    x0 = max(int(min(ax, bx, cx)), 0)
    x1 = min(int(max(ax, bx, cx)) + 1, inWidth - 1)
    y0 = max(int(min(ay, by, cy)), 0)
    y1 = min(int(max(ay, by, cy)) + 1, inHeight - 1)
    if x0 > x1 or y0 > y1:
        return []
    sign = 1.0 if area > 0.0 else -1.0
    out: List[int] = []
    for y in range(y0, y1 + 1):
        py = y + 0.5
        row = y * inWidth
        for x in range(x0, x1 + 1):
            px = x + 0.5
            if ((bx - ax) * (py - ay) - (by - ay) * (px - ax)) * sign < 0.0:
                continue
            if ((cx - bx) * (py - by) - (cy - by) * (px - bx)) * sign < 0.0:
                continue
            if ((ax - cx) * (py - cy) - (ay - cy) * (px - cx)) * sign < 0.0:
                continue
            out.append(row + x)
    return out


def rasterize_triangle(inImage: MaskImage, inTriangle: Triangle, inValue: int = DEFAULT_VALUE) -> int:
    """픽셀 중심이 삼각형 안(경계 포함)인 픽셀을 칠한다.

    Args:
        inImage: 대상 이미지(제자리 수정)
        inTriangle: 픽셀 좌표 삼각형
        inValue: 칠할 값

    Returns:
        중심이 안에 있는 픽셀 수(이미 같은 값이었어도 센다 - 면의 커버 통계용)
    """
    indices = triangle_pixel_indices(inTriangle, inImage.width, inImage.height)
    pixels = inImage.pixels
    for i in indices:
        pixels[i] = inValue
    return len(indices)


def rasterize_polygon(inImage: MaskImage, inPoints: Sequence[Point], inValue: int = DEFAULT_VALUE) -> int:
    """폴리곤(픽셀 좌표)을 팬 삼각분할해 칠한다. 중심이 안에 있는 **고유** 픽셀 수를 돌려준다.

    팬 삼각형들이 공유하는 대각선 위의 픽셀 중심은 두 삼각형이 함께 세므로, 폴리곤 단위로 집합을 모아
    한 번만 센다(면의 커버 통계가 겹침으로 부풀지 않게 한다).
    """
    width, height = inImage.width, inImage.height
    covered: Set[int] = set()
    for tri in triangulate_fan(inPoints):
        covered.update(triangle_pixel_indices(tri, width, height))
    pixels = inImage.pixels
    for i in covered:
        pixels[i] = inValue
    return len(covered)


def dilate(inImage: MaskImage, inPixels: int, inValue: int = DEFAULT_VALUE) -> MaskImage:
    """값이 inValue인 영역을 8-이웃으로 inPixels만큼 팽창한 새 이미지를 돌려준다.

    Args:
        inImage: 원본(바뀌지 않는다)
        inPixels: 팽창 픽셀 수(0이면 사본 그대로)
        inValue: 팽창할 값

    Returns:
        팽창된 사본

    Raises:
        ValueError: inPixels가 음수
    """
    if inPixels < 0:
        raise ValueError(f"팽창 픽셀 수는 0 이상이어야 한다: {inPixels}")
    current = inImage.copy()
    width, height = current.width, current.height
    for _ in range(inPixels):
        src = current.pixels
        dst = bytearray(src)
        for y in range(height):
            row = y * width
            for x in range(width):
                if src[row + x] != inValue:
                    continue
                for dy in (-1, 0, 1):
                    ny = y + dy
                    if ny < 0 or ny >= height:
                        continue
                    nrow = ny * width
                    for dx in (-1, 0, 1):
                        nx = x + dx
                        if 0 <= nx < width:
                            dst[nrow + nx] = inValue
        current.pixels = dst
    return current


@dataclass
class BakeStats:
    """베이크 커버 통계.

    Attributes:
        faceCount: 요청한 면 수
        paintedPixels: 칠한 값의 픽셀 수(팽창 포함, 최종 이미지 기준)
        zeroPixelFaces: 픽셀 중심을 하나도 덮지 못한 면 수
        perFacePixels: 면별 커버 픽셀 수(요청 순서)
    """

    faceCount: int = 0
    paintedPixels: int = 0
    zeroPixelFaces: int = 0
    perFacePixels: List[int] = field(default_factory=list)

    def as_dict(self) -> Dict[str, int]:
        """요약 사전(면별 목록 제외)."""
        return {
            "faceCount": self.faceCount,
            "paintedPixels": self.paintedPixels,
            "zeroPixelFaces": self.zeroPixelFaces,
        }


def bake_face_mask(
    inMapVerts: Sequence[Uv],
    inMapFaces: Sequence[Sequence[int]],
    inFaceIndices: Sequence[int],
    inSize: int,
    inPadding: int = 0,
    inFill: int = DEFAULT_FILL,
    inValue: int = DEFAULT_VALUE,
) -> Tuple[MaskImage, BakeStats]:
    """면 집합을 정사각 마스크로 굽는다.

    Args:
        inMapVerts: 맵 버텍스 (u, v) 목록
        inMapFaces: 면별 맵 버텍스 인덱스 목록(0-based)
        inFaceIndices: 칠할 면 인덱스(0-based)
        inSize: 이미지 한 변 픽셀 수
        inPadding: 팽창 픽셀 수(0이면 없음)
        inFill: 바탕값
        inValue: 칠할 값

    Returns:
        (이미지, 통계)

    Raises:
        ValueError: 크기·값 범위 밖, 면 인덱스가 범위 밖
        IndexError: 맵 면이 가리키는 맵 버텍스가 없음
    """
    _check_value(inValue)
    image = MaskImage(inSize, inSize, inFill)
    stats = BakeStats(faceCount=len(inFaceIndices))
    faceCount = len(inMapFaces)
    for faceIndex in inFaceIndices:
        if faceIndex < 0 or faceIndex >= faceCount:
            raise ValueError(f"면 인덱스가 범위 밖이다: {faceIndex} (면 수 {faceCount})")
        points = [uv_to_pixel(inMapVerts[i], inSize, inSize) for i in inMapFaces[faceIndex]]
        painted = rasterize_polygon(image, points, inValue)
        stats.perFacePixels.append(painted)
        if painted == 0:
            stats.zeroPixelFaces += 1
    if inPadding > 0:
        image = dilate(image, inPadding, inValue)
    stats.paintedPixels = image.count(inValue)
    return image, stats


def write_tga(inPath: str, inImage: MaskImage) -> str:
    """비압축 24-bit TGA(원점 좌하단)로 기록한다. 부모 폴더가 없으면 만든다.

    Args:
        inPath: 출력 파일 경로
        inImage: 이미지

    Returns:
        기록한 경로
    """
    parent = os.path.dirname(os.path.abspath(inPath))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    header = struct.pack(
        "<BBBHHBHHHHBB",
        0,  # id length
        0,  # color map type
        TGA_TYPE_TRUECOLOR,
        0,
        0,
        0,  # color map spec
        0,
        0,  # x/y origin
        inImage.width,
        inImage.height,
        24,  # pixel depth
        0,  # descriptor: 좌하단 원점
    )
    width = inImage.width
    body = bytearray()
    for y in range(inImage.height - 1, -1, -1):
        row = inImage.pixels[y * width : (y + 1) * width]
        for v in row:
            body += bytes((v, v, v))
    with open(inPath, "wb") as f:
        f.write(header)
        f.write(body)
    return inPath


def read_tga(inPath: str) -> MaskImage:
    """비압축 24/32-bit TGA를 1채널(R)로 읽는다(테스트·검증용).

    Args:
        inPath: TGA 경로

    Returns:
        이미지(행 0 = 위)

    Raises:
        ValueError: 지원하지 않는 형식
    """
    with open(inPath, "rb") as f:
        data = f.read()
    if len(data) < TGA_HEADER_SIZE:
        raise ValueError("TGA 헤더가 짧다")
    idLength, colorMapType, imageType, _, _, _, _, _, width, height, depth, descriptor = struct.unpack(
        "<BBBHHBHHHHBB", data[:TGA_HEADER_SIZE]
    )
    if colorMapType != 0 or imageType != TGA_TYPE_TRUECOLOR or depth not in (24, 32):
        raise ValueError(f"지원하지 않는 TGA: type={imageType} depth={depth} colorMap={colorMapType}")
    bpp = depth // 8
    offset = TGA_HEADER_SIZE + idLength
    needed = width * height * bpp
    if len(data) < offset + needed:
        raise ValueError("TGA 픽셀 데이터가 짧다")
    image = MaskImage(width, height)
    topLeft = bool(descriptor & TGA_DESCRIPTOR_TOP_LEFT)
    for fileRow in range(height):
        y = fileRow if topLeft else (height - 1 - fileRow)
        start = offset + fileRow * width * bpp
        rowBytes = data[start : start + width * bpp]
        # BGR(A) - R은 세 번째 바이트
        image.pixels[y * width : (y + 1) * width] = bytes(rowBytes[2::bpp])
    return image


def tga_header_info(inPath: str) -> Dict[str, int]:
    """TGA 헤더 필드(테스트용)."""
    with open(inPath, "rb") as f:
        head = f.read(TGA_HEADER_SIZE)
    fields = struct.unpack("<BBBHHBHHHHBB", head)
    return {
        "idLength": fields[0],
        "colorMapType": fields[1],
        "imageType": fields[2],
        "width": fields[8],
        "height": fields[9],
        "depth": fields[10],
        "descriptor": fields[11],
    }


def face_indices_or_empty(inFaces: Optional[Sequence[int]]) -> List[int]:
    """None을 빈 목록으로(호출 편의)."""
    return list(inFaces) if inFaces else []
