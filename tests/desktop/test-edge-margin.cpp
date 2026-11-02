#include "../../.config/hypr/plugins/bubble-reserve/geometry.hpp"
#include <iomanip>
#include <iostream>
int main() {
    BubbleReserve::Rect box, obstacle;
    while (std::cin >> box.x >> box.y >> box.w >> box.h >> obstacle.x >> obstacle.y
                    >> obstacle.w >> obstacle.h >> obstacle.gapX >> obstacle.gapY) {
        const auto result = BubbleReserve::project(box, {obstacle}, 0);
        std::cout << std::setprecision(12) << result.x << ' ' << result.y << ' '
                  << result.w << ' ' << result.h << '\n';
    }
}
