import AppKit

enum Style: String { case ring, track }

struct Indicators {
    let defaults: UserDefaults
    var style: Style { Style(rawValue: defaults.string(forKey: "indicatorStyle") ?? "") ?? .ring }
    var ringParts: Int { defaults.string(forKey: "timeDisplay") == "hidden" ? 1 : 3 }
    var parts: Int {
        guard style == .track else { return ringParts }
        let saved = defaults.integer(forKey: "trackParts")
        return (1...3).contains(saved) ? saved : ringParts
    }
    func toggle(_ bit: Int) {
        if style == .ring {
            if bit == 2 {
                if defaults.object(forKey: "trackParts") == nil { defaults.set(ringParts, forKey: "trackParts") }
                defaults.set(parts == 3 ? "hidden" : "shown", forKey: "timeDisplay")
            }
        } else {
            let next = parts ^ bit
            if (1...3).contains(next) { defaults.set(next, forKey: "trackParts") }
        }
    }
}

let timeFont = NSFont.monospacedDigitSystemFont(ofSize: 12, weight: .semibold)

func trackImage(number: String, marker: String, time: String, parts: Int, fraction: Double?) -> NSImage {
    var labels = [NSAttributedString]()
    if parts & 1 != 0 {
        let font = quotaFont(for: number)
        labels += [ink(marker, font), ink(number, font)]
    }
    if parts == 3 { labels.append(ink("·", timeFont)) }
    if parts & 2 != 0 { labels.append(ink(time, timeFont)) }
    let width = max(28, 16 + labels.reduce(CGFloat(0)) { $0 + ceil($1.size().width) } + CGFloat(labels.count-1)*3)
    let image = NSImage(size: NSSize(width: width, height: 24), flipped: false) { rect in
        let radius: CGFloat = 10.7, left = 1.5 + radius, right = rect.width-left
        let path = NSBezierPath()
        path.move(to: NSPoint(x: left, y: 12+radius))
        path.appendArc(withCenter: NSPoint(x: left, y: 12), radius: radius, startAngle: 90, endAngle: 270)
        path.line(to: NSPoint(x: right, y: 12-radius))
        path.appendArc(withCenter: NSPoint(x: right, y: 12), radius: radius, startAngle: -90, endAngle: 90)
        path.close()
        path.lineWidth = 2.4
        NSColor.black.withAlphaComponent(0.28).setStroke()
        path.stroke()
        if let progress = fraction, progress > 0 {
            let length = 2*(right-left) + 2 * .pi * radius
            if progress < 1 { path.setLineDash([length*progress, length*2], count: 2, phase: 0) }
            path.lineCapStyle = .round
            NSColor.black.setStroke()
            path.stroke()
        }
        var x: CGFloat = 8
        for label in labels {
            label.draw(at: NSPoint(x: x, y: 12-label.size().height/2))
            x += ceil(label.size().width)+3
        }
        return true
    }
    image.isTemplate = true
    return image
}
